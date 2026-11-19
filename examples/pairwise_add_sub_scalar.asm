.equ SPACE_CHAR, 32

.data

vec_a: .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
vec_b: .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
vec_c: .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

.text

.globl _start

.extern print_char
.extern print_newline
.extern read_int
.extern print_signed

_start:
    bl read_int
    addi r6, r3, 0              # r6 = N (pairs_count)
    li r10, 0                   # r10 = pair_index
    li r11, 0                   # r11 = input_offset

read_pair_loop:
    cmpw r10, r6
    bge calculate

    bl read_int
    li r13, vec_a
    add r13, r13, r11
    stw r3, 0(r13)

    bl read_int
    li r13, vec_b
    add r13, r13, r11
    stw r3, 0(r13)

    addi r11, r11, 4
    addi r10, r10, 1
    b read_pair_loop

calculate:
    li r10, 0
    li r11, 0
    li r12, 0                   # r12 = output_offset

calculate_loop:
    cmpw r10, r6
    bge print_results

    li r13, vec_a
    add r13, r13, r11
    lwz r4, 0(r13)
    li r13, vec_b
    add r13, r13, r11
    lwz r5, 0(r13)

    add r8, r4, r5
    sub r9, r4, r5

    li r13, vec_c
    add r13, r13, r12
    stw r8, 0(r13)
    stw r9, 4(r13)

    addi r12, r12, 8
    addi r11, r11, 4
    addi r10, r10, 1
    b calculate_loop

print_results:
    slwi r13, r6, 1
    li r14, 0
    li r15, vec_c

print_loop:
    cmpw r14, r13
    bge exit
    lwz r3, 0(r15)
    bl print_signed
    addi r14, r14, 1
    addi r15, r15, 4
    cmpw r14, r13
    bge print_done
    li r3, SPACE_CHAR
    bl print_char
    b print_loop

print_done:
    bl print_newline

exit:
    trap