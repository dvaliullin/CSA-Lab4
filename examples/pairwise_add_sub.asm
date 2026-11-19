.equ SPACE_CHAR, 32

.data

vec_a:   .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
vec_b:   .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
vec_add: .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
vec_sub: .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

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
    
calculate_loop:
    cmpw r10, r6
    bge print_results

    li r13, vec_a
    add r13, r13, r11
    lvx v0, 0(r13)
    li r13, vec_b
    add r13, r13, r11
    lvx v1, 0(r13)
    vadduwm v2, v0, v1
    vsubuwm v3, v0, v1

    li r13, vec_add
    add r13, r13, r11
    stvx v2, 0(r13)
    li r13, vec_sub
    add r13, r13, r11
    stvx v3, 0(r13)
    addi r10, r10, 4
    addi r11, r11, 16
    b calculate_loop

print_results:
    li r14, 0                   # r14 = pair_index
    subi r15, r6, 1             # r15 = N - 1 (last pair index)

print_loop:
    cmpw r14, r6
    bge exit

    slwi r13, r14, 2
    li r9, vec_add
    add r9, r9, r13
    lwz r3, 0(r9)
    bl print_signed

    li r3, SPACE_CHAR
    bl print_char

    li r9, vec_sub
    add r9, r9, r13
    lwz r3, 0(r9)
    bl print_signed

    addi r14, r14, 1
    cmpw r14, r6
    bge print_done
    li r3, SPACE_CHAR
    bl print_char
    b print_loop

print_done:
    bl print_newline

exit:
    trap