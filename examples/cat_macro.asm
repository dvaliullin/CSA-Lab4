.equ INPUT_ADDR,  0xFFFF_0000
.equ OUTPUT_ADDR, 0xFFFF_0004
.equ EOF,         -1

.macro read_char dst
    lis r11, @h(INPUT_ADDR)
    addi r11, r11, @l(INPUT_ADDR)
    lwz \dst, 0(r11)
.endm

.macro write_char src
    lis r12, @h(OUTPUT_ADDR)
    addi r12, r12, @l(OUTPUT_ADDR)
    stw \src, 0(r12)
.endm

.text

.globl _start

_start:

loop:
    read_char r3

    cmpwi r3, EOF
    beq exit

    write_char r3

    b loop

exit:
    trap