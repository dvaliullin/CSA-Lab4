.text

.globl _start

.extern read_int
.extern print_int
.extern print_newline

_start:
    bl read_int             # r3 = n
    li r4, 0                # r4 = count
    li r10, 2

loop:
    cmpwi r3, 1
    beq exit
    addi r4, r4, 1          # count += 1

    modw r5, r3, r10        # r5 = n % 2
    cmpwi r5, 0
    beq n_is_even

n_is_odd:
    li r6, 3
    mullw r3, r3, r6        # n *= 3
    addi r3, r3, 1          # r3 = 3n + 1
    b loop

n_is_even:
    divw r3, r3, r10        # n /= 2
    b loop

exit:
    addi r3, r4, 0
    bl print_int
    bl print_newline
    trap