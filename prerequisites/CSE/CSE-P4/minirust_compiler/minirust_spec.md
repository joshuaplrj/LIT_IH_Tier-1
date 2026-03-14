# MiniRust Language Specification

## Types
- `i32`  — 32-bit signed integer
- `f64`  — 64-bit floating point
- `bool` — boolean (true / false)
- `String` — owned heap string
- `&str`  — borrowed string slice
- `Vec<i32>` — growable integer vector

## Variables
```
let x: i32 = 5;
let mut y: f64 = 3.14;
```

## Functions
```
fn add(a: i32, b: i32) -> i32 {
    return a + b;
}
```

## Ownership
- `let x = String::new("hello");`  — moves ownership into x
- `let y = &x;`                    — immutable borrow
- `let z = &mut x;`                — mutable borrow (x must be `mut`)
- Assignment moves ownership for String/Vec; primitive types are copied.

## Control Flow
```
if condition { ... } else { ... }
while condition { ... }
for item in collection { ... }
```

## Operators
`+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `>`, `<=`, `>=`, `&&`, `||`, `!`

## Printing
```
println!("{}", x);
println!("{} {}", a, b);
```

## Vec Operations
```
let mut v: Vec<i32> = Vec::new();
v.push(1);
let n = v.len();
let first = v[0];
```
