.equ SPACE_CHAR, 32
.equ LF, 10
.equ EOF, -1
.equ LEFT_PAREN, 40
.equ RIGHT_PAREN, 41
.equ PLUS_CHAR, 43
.equ MINUS_CHAR, 45
.equ MUL_CHAR, 42
.equ DIV_CHAR, 47
.equ ZERO_CHAR, 48
.equ NINE_CHAR, 57
.equ STACK_TOP, 0xFFFF_FFFF

.text

.globl _start

.extern read_char
.extern print_char
.extern print_newline

_start:
    li sp, STACK_TOP
    li r14, 0                   # r14 = space_flag
    li r15, 0                   # r15 = separate_digits_flag

token_loop:
    bl read_char
    cmpwi r3, EOF
    beq flush_stack
    cmpwi r3, LF
    beq flush_stack
    addi r6, r3, 0              # r6 = current_char

    cmpwi r6, SPACE_CHAR
    beq token_space

    cmpwi r6, ZERO_CHAR
    blt check_left
    cmpwi r6, NINE_CHAR
    bgt check_left

    cmpwi r15, 0
    bne print_digit

separate_digits:
    cmpwi r14, 0
    beq print_digit
    li r3, SPACE_CHAR
    bl print_char

print_digit:
    li r14, 1
    li r15, 1
    addi r3, r6, 0
    bl print_char
    b token_loop

token_space:
    li r15, 0
    b token_loop

check_left:
    cmpwi r6, LEFT_PAREN
    bne check_right
    li r15, 0
    subi sp, sp, 4
    stw r6, 0(sp)
    b token_loop

check_right:
    cmpwi r6, RIGHT_PAREN
    bne handle_operator
    li r15, 0

pop_right:
    li r10, STACK_TOP
    cmpw sp, r10
    bge token_loop
    lwz r9, 0(sp)
    addi sp, sp, 4
    cmpwi r9, LEFT_PAREN
    beq token_loop

    cmpwi r14, 0
    beq print_right_op
    li r3, SPACE_CHAR
    bl print_char

print_right_op:
    li r14, 1
    addi r3, r9, 0
    bl print_char
    b pop_right

handle_operator:
    li r15, 0
    li r11, 1                   # r11 = current_prio (1 for +,-; 2 for *,/)
    cmpwi r6, MUL_CHAR
    beq priority_two
    cmpwi r6, DIV_CHAR
    beq priority_two
    b stack_priority

priority_two:
    li r11, 2

stack_priority:
    li r10, STACK_TOP
    cmpw sp, r10
    bge push_operator
    lwz r9, 0(sp)
    cmpwi r9, LEFT_PAREN
    beq push_operator

    li r13, 1                   # r13 = stack_top_prio
    cmpwi r9, MUL_CHAR
    beq top_priority_two
    cmpwi r9, DIV_CHAR
    beq top_priority_two
    b compare_priority

top_priority_two:
    li r13, 2

compare_priority:
    cmpw r13, r11
    blt push_operator

    lwz r9, 0(sp)
    addi sp, sp, 4
    cmpwi r14, 0
    beq print_operator
    li r3, SPACE_CHAR
    bl print_char

print_operator:
    li r14, 1
    addi r3, r9, 0
    bl print_char
    b stack_priority

push_operator:
    subi sp, sp, 4
    stw r6, 0(sp)
    b token_loop

flush_stack:
    li r10, STACK_TOP
    cmpw sp, r10
    bge exit
    lwz r9, 0(sp)
    addi sp, sp, 4
    cmpwi r9, LEFT_PAREN
    beq flush_stack

    cmpwi r14, 0
    beq print_flush
    li r3, SPACE_CHAR
    bl print_char

print_flush:
    li r14, 1
    addi r3, r9, 0
    bl print_char
    b flush_stack

exit:
    bl print_newline
    li sp, STACK_TOP
    trap
