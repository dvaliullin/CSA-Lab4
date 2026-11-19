.equ SPACE_CHAR, 32

.text

.globl _start

.extern read_int
.extern print_char
.extern print_int
.extern print_newline

_start:
    bl read_int
    addi r4, r3, 0              # r4 = N (array_length)
    slwi r5, r4, 2              # r5 = N * 2
    sub sp, sp, r5

    li r6, 0                    # r6 = input_index

read_array:
    cmpw r6, r4
    bge start_sort
    bl read_int
    slwi r7, r6, 2
    add r7, sp, r7
    stw r3, 0(r7)
    addi r6, r6, 1
    b read_array

start_sort:
    subi r5, r4, 1              # r5 = N - 1

outer_loop:
    cmpwi r5, 0
    ble sort_done
    li r6, 0

inner_loop:
    cmpw r6, r5
    bge next_outer

    slwi r7, r6, 2
    add r7, sp, r7
    lwz r8, 0(r7)
    lwz r9, 4(r7)
    cmpw r8, r9
    ble no_swap
    stw r9, 0(r7)
    stw r8, 4(r7)

no_swap:
    addi r6, r6, 1
    b inner_loop

next_outer:
    subi r5, r5, 1
    b outer_loop

sort_done:
    li r6, 0
    subi r14, r4, 1

print_array:
    cmpw r6, r4
    bge restore

    slwi r7, r6, 2
    add r7, sp, r7
    lwz r3, 0(r7)
    bl print_int

    cmpw r6, r14
    bge print_done
    li r3, SPACE_CHAR
    bl print_char
    addi r6, r6, 1
    b print_array

print_done:
    bl print_newline
    slwi r7, r4, 2
    add sp, sp, r7
    b exit

restore:
    bl print_newline
    slwi r7, r4, 2
    add sp, sp, r7

exit:
    trap
