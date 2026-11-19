.data

msg: .pstr "Hello, World!"

.text

.globl _start

.extern print_pstr

_start:
    li r3, msg
    bl print_pstr
    bl print_newline
    trap