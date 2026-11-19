.equ INPUT_ADDR,  0xFFFF_0000
.equ OUTPUT_ADDR, 0xFFFF_0004
.equ EOF,         -1

.text

.globl _start

_start:
    lis r4, @h(INPUT_ADDR)
    addi r4, r4, @l(INPUT_ADDR)
    lis r5, @h(OUTPUT_ADDR)
    addi r5, r5, @l(OUTPUT_ADDR)

loop:
    lwz r3, 0(r4)            # read char
    cmpwi r3, EOF            # check EOF
    beq exit
    stw r3, 0(r5)            # print char
    b loop

exit:
    trap