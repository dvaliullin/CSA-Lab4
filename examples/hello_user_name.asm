.data

question:        .pstr "What is your name?\n"
greeting_prefix: .pstr "Hello, "
greeting_suffix: .pstr "!\n"

buffer:          .word 0, 0, 0, 0, 0, 0, 0, 0

.text

.globl _start

.extern print_pstr
.extern read_pstr

_start:
    li r3, question
    bl print_pstr

    li r3, buffer
    bl read_pstr

    li r3, greeting_prefix
    bl print_pstr

    li r3, buffer
    bl print_pstr

    li r3, greeting_suffix
    bl print_pstr

    trap