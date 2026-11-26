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
    li r18, STACK_TOP           # r18 = STACK_TOP
    li r16, 0                   # r16 = space_flag
    li r17, 0                   # r17 = separate_digits_flag

token_loop:
    bl read_char
    cmpwi r3, EOF
    beq flush_stack
    cmpwi r3, LF
    beq flush_stack
    addi r19, r3, 0             # r19 = current_char

    cmpwi r19, SPACE_CHAR
    beq token_space

    cmpwi r19, ZERO_CHAR
    blt check_left
    cmpwi r19, NINE_CHAR
    bgt check_left

    cmpwi r17, 0
    bne print_digit

separate_digits:
    cmpwi r16, 0
    beq print_digit
    li r3, SPACE_CHAR
    bl print_char

print_digit:
    li r16, 1
    li r17, 1
    addi r3, r19, 0
    bl print_char
    b token_loop

token_space:
    li r17, 0
    b token_loop

check_left:
    cmpwi r19, LEFT_PAREN
    bne check_right
    li r17, 0
    subi sp, sp, 4
    stw r19, 0(sp)
    b token_loop

check_right:
    cmpwi r19, RIGHT_PAREN
    bne handle_operator
    li r17, 0

pop_right:
    cmpw sp, r18
    bge token_loop
    lwz r20, 0(sp)
    addi sp, sp, 4
    cmpwi r20, LEFT_PAREN
    beq token_loop

    cmpwi r16, 0
    beq print_right_op
    li r3, SPACE_CHAR
    bl print_char

print_right_op:
    li r16, 1
    addi r3, r20, 0
    bl print_char
    b pop_right

handle_operator:
    li r17, 0
    li r21, 1                   # r21 = current_prio (1 for +,-; 2 for *,/)
    cmpwi r19, MUL_CHAR
    beq priority_two
    cmpwi r19, DIV_CHAR
    beq priority_two
    b stack_priority

priority_two:
    li r21, 2

stack_priority:
    cmpw sp, r18
    bge push_operator
    lwz r20, 0(sp)
    cmpwi r20, LEFT_PAREN
    beq push_operator

    li r22, 1                   # r22 = stack_top_prio
    cmpwi r20, MUL_CHAR
    beq top_priority_two
    cmpwi r20, DIV_CHAR
    beq top_priority_two
    b compare_priority

top_priority_two:
    li r22, 2

compare_priority:
    cmpw r22, r21
    blt push_operator

    lwz r20, 0(sp)
    addi sp, sp, 4
    cmpwi r16, 0
    beq print_operator
    li r3, SPACE_CHAR
    bl print_char

print_operator:
    li r16, 1
    addi r3, r20, 0
    bl print_char
    b stack_priority

push_operator:
    subi sp, sp, 4
    stw r19, 0(sp)
    b token_loop

flush_stack:
    cmpw sp, r18
    bge exit
    lwz r20, 0(sp)
    addi sp, sp, 4
    cmpwi r20, LEFT_PAREN
    beq flush_stack

    cmpwi r16, 0
    beq print_flush
    li r3, SPACE_CHAR
    bl print_char

print_flush:
    li r16, 1
    addi r3, r20, 0
    bl print_char
    b flush_stack

exit:
    bl print_newline
    li sp, STACK_TOP
    trap