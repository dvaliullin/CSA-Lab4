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
    addi r16, r3, 0             # r16 = N (pairs_count)
    li r17, 0                   # r17 = pair_index
    li r18, 0                   # r18 = input_offset
    li r20, vec_a               # r20 = &vec_a
    li r21, vec_b               # r21 = &vec_b
    li r22, vec_c               # r22 = &vec_c

read_pair_loop:
    cmpw r17, r16
    bge calculate

    bl read_int
    add r4, r20, r18
    stw r3, 0(r4)

    bl read_int
    add r4, r21, r18
    stw r3, 0(r4)

    addi r18, r18, 4
    addi r17, r17, 1
    b read_pair_loop

calculate:
    li r17, 0
    li r18, 0
    li r19, 0                   # r19 = output_offset

calculate_loop:
    cmpw r17, r16
    bge print_results

    add r4, r20, r18
    lwz r5, 0(r4)
    add r4, r21, r18
    lwz r6, 0(r4)

    add r7, r5, r6
    sub r8, r5, r6

    add r4, r22, r19
    stw r7, 0(r4)
    stw r8, 4(r4)

    addi r19, r19, 8
    addi r18, r18, 4
    addi r17, r17, 1
    b calculate_loop

print_results:
    slwi r23, r16, 1            # r23 = 2 * N
    li r24, 0                   # r24 = print_index
    addi r25, r22, 0            # r25 = print_ptr

print_loop:
    cmpw r24, r23
    bge exit
    lwz r3, 0(r25)
    bl print_signed
    addi r24, r24, 1
    addi r25, r25, 4
    cmpw r24, r23
    bge print_done
    li r3, SPACE_CHAR
    bl print_char
    b print_loop

print_done:
    bl print_newline

exit:
    trap