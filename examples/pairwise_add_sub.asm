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
    addi r16, r3, 0             # r16 = N (pairs_count)
    li r17, 0                   # r17 = pair_index
    li r18, 0                   # r18 = input_offset
    li r19, vec_a               # r19 = &vec_a
    li r20, vec_b               # r20 = &vec_b
    li r21, vec_add             # r21 = &vec_add
    li r22, vec_sub             # r22 = &vec_sub

read_pair_loop:
    cmpw r17, r16
    bge calculate

    bl read_int
    add r4, r19, r18
    stw r3, 0(r4)

    bl read_int
    add r4, r20, r18
    stw r3, 0(r4)

    addi r18, r18, 4
    addi r17, r17, 1
    b read_pair_loop

calculate:
    li r17, 0
    li r18, 0

calculate_loop:
    cmpw r17, r16
    bge print_results

    add r4, r19, r18
    lvx v0, 0(r4)
    add r4, r20, r18
    lvx v1, 0(r4)
    vadduwm v2, v0, v1
    vsubuwm v3, v0, v1

    add r4, r21, r18
    stvx v2, 0(r4)
    add r4, r22, r18
    stvx v3, 0(r4)

    addi r17, r17, 4
    addi r18, r18, 16
    b calculate_loop

print_results:
    li r17, 0                   # r17 = pair_index

print_loop:
    cmpw r17, r16
    bge exit

    slwi r23, r17, 2
    add r4, r21, r23
    lwz r3, 0(r4)
    bl print_signed

    li r3, SPACE_CHAR
    bl print_char

    add r4, r22, r23
    lwz r3, 0(r4)
    bl print_signed

    addi r17, r17, 1
    cmpw r17, r16
    bge print_done
    li r3, SPACE_CHAR
    bl print_char
    b print_loop

print_done:
    bl print_newline

exit:
    trap