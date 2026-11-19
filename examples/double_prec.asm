.equ ZERO_CHAR, 48

.data

a_lo:   .word 0xFFFFFFFF
a_hi:   .word 0x00000001
b_lo:   .word 0x00000002
b_hi:   .word 0x00000002
res_lo: .word 0
res_hi: .word 0

.text

.globl _start

.extern print_char
.extern print_newline

_start:
    lwz r3, a_lo(r0)
    lwz r4, a_hi(r0)
    lwz r5, b_lo(r0)
    lwz r6, b_hi(r0)

    add r7, r3, r5              # r7 = res_lo = a_lo + b_lo
    li r9, 0                    # r9 = carry = 0

    cmplw r7, r3
    bge calc_hi

    li r9, 1                    # carry = 1

calc_hi:
    add r8, r4, r6
    add r8, r8, r9              # r8 = res_hi = a_hi + b_hi + carry

    stw r7, res_lo(r0)
    stw r8, res_hi(r0)

    addi r3, r8, ZERO_CHAR      # r3 = res_hi + '0'
    bl print_char

    lwz r7, res_lo(r0)
    addi r3, r7, ZERO_CHAR      # r3 = res_lo + '0'
    bl print_char

    bl print_newline
    trap