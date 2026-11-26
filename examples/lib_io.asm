.equ INPUT_ADDR,  0xFFFF_0000
.equ OUTPUT_ADDR, 0xFFFF_0004
.equ LF,          10
.equ EOF          -1
.equ ZERO_CHAR,   48
.equ MINUS_CHAR,  45
.equ SPACE_CHAR,  32
.equ COMMA_CHAR,  44
.equ PLUS_CHAR,   43
.equ NUL,         0
.equ TAB,         9

.text

.globl print_pstr
.globl print_char
.globl print_int
.globl read_char
.globl read_pstr
.globl print_newline
.globl read_int
.globl print_signed

# Функция вывода pstr, принимает адрес строки в r3
print_pstr:
    mflr r12
    addi sp, sp, -12
    stw r12, 0(sp)
    stw r4, 4(sp)
    stw r5, 8(sp)
    lbz r4, 0(r3)               # r4 = pstr_length
    addi r5, r3, 1              # r5 = pstr_char_ptr

print_pstr_loop:
    cmpwi r4, 0
    beq print_pstr_done
    lbz r3, 0(r5)               # read char
    bl print_char
    addi r5, r5, 1
    subi r4, r4, 1
    b print_pstr_loop

print_pstr_done:
    lwz r5, 8(sp)
    lwz r4, 4(sp)
    lwz r12, 0(sp)
    addi sp, sp, 12
    mtlr r12
    blr                         # return

# Функция вывода одного символа, принимает код символа в r3
print_char:
    addi sp, sp, -4
    stw r7, 0(sp)
    lis r7, @h(OUTPUT_ADDR)
    addi r7, r7, @l(OUTPUT_ADDR)
    stw r3, 0(r7)
    lwz r7, 0(sp)
    addi sp, sp, 4
    blr

# Функция вывода целого неотрицательного числа из r3
print_int:
    mflr r12
    addi sp, sp, -40
    stw r12, 0(sp)
    stw r4, 4(sp)
    stw r5, 8(sp)
    stw r6, 12(sp)
    stw r7, 16(sp)
    stw r8, 20(sp)

    cmpwi r3, 0
    bne convert
    li r3, ZERO_CHAR
    bl print_char
    b pi_restore

convert:
    addi r4, sp, 24
    li r6, 0                    # r6 = digits_counter

convert_loop:
    li r8, 10
    divw r7, r3, r8
    modw r5, r3, r8
    addi r5, r5, ZERO_CHAR
    stb r5, 0(r4)
    addi r4, r4, 1
    addi r6, r6, 1
    addi r3, r7, 0
    cmpwi r3, 0
    bne convert_loop            # if number / 10 == 0, stop convert

output_loop:
    subi r4, r4, 1
    lbz r3, 0(r4)
    bl print_char
    subi r6, r6, 1
    cmpwi r6, 0
    bne output_loop

pi_restore:
    lwz r12, 0(sp)
    lwz r4, 4(sp)
    lwz r5, 8(sp)
    lwz r6, 12(sp)
    lwz r7, 16(sp)
    lwz r8, 20(sp)
    addi sp, sp, 40
    mtlr r12
    blr

# Функция переноса строки ('\n')
print_newline:
    mflr r12
    addi sp, sp, -4
    stw r12, 0(sp)
    li r3, LF
    bl print_char
    lwz r12, 0(sp)
    addi sp, sp, 4
    mtlr r12
    blr

# Функция чтения одного символа из потока ввода, возвращает прочитанный байт в r3
read_char:
    addi sp, sp, -4
    stw r7, 0(sp)
    lis r7, @h(INPUT_ADDR)
    addi r7, r7, @l(INPUT_ADDR)
    lwz r3, 0(r7)
    lwz r7, 0(sp)
    addi sp, sp, 4
    blr

# Функция чтения строки из потока ввода, принимает адрес буфера для записи строки в r3
read_pstr:
    mflr r12
    addi sp, sp, -16
    stw r12, 0(sp)
    stw r4, 4(sp)
    stw r5, 8(sp)
    stw r6, 12(sp)
    addi r6, r3, 0              # r6 = pstr_addr
    addi r5, r3, 1              # r5 = pstr_char_ptr
    li r4, 0                    # r4 = pstr_length

read_pstr_loop:
    bl read_char
    cmpwi r3, EOF
    beq read_pstr_done
    cmpwi r3, LF
    beq read_pstr_done
    stb r3, 0(r5)
    addi r5, r5, 1
    addi r4, r4, 1
    b read_pstr_loop

read_pstr_done:
    stb r4, 0(r6)
    lwz r6, 12(sp)
    lwz r5, 8(sp)
    lwz r4, 4(sp)
    lwz r12, 0(sp)
    addi sp, sp, 16
    mtlr r12
    blr

# Функция чтения знакового числа из потока ввода, пропуская пробелы, запятые и переносы строк ('\n'), обрабатывая '-'
# Возвращает прочитанное число в r3
read_int:
    mflr r12
    subi sp, sp, 24
    stw r12, 20(sp)
    stw r4, 16(sp)
    stw r5, 12(sp)
    stw r6, 8(sp)
    stw r9, 4(sp)
    stw r8, 0(sp)
    li r6, 0
    li r8, 1                    # r8 = neg_pos_flag
    li r4, 10

skip:
    bl read_char
    addi r5, r3, 0
    cmpwi r5, EOF
    beq read_done
    cmpwi r5, SPACE_CHAR
    ble skip
    cmpwi r5, COMMA_CHAR
    beq skip
    cmpwi r5, MINUS_CHAR
    bne handle_plus
    li r8, -1
    bl read_char
    addi r5, r3, 0
    b handle_digit

handle_plus:
    cmpwi r5, PLUS_CHAR
    bne handle_digit
    bl read_char
    addi r5, r3, 0

handle_digit:
    subi r9, r5, ZERO_CHAR
    cmpwi r9, NUL
    blt read_done
    cmpwi r9, TAB
    bgt read_done
    mullw r6, r6, r4
    add r6, r6, r9
    bl read_char
    addi r5, r3, 0
    b handle_digit

read_done:
    cmpwi r8, 1
    bne negative
    addi r3, r6, 0
    b ri_restore

negative:
    sub r3, r0, r6

ri_restore:
    lwz r8, 0(sp)
    lwz r9, 4(sp)
    lwz r6, 8(sp)
    lwz r5, 12(sp)
    lwz r4, 16(sp)
    lwz r12, 20(sp)
    addi sp, sp, 24
    mtlr r12
    blr

# Функция вывода знакового числа из r3
print_signed:
    mflr r12
    addi sp, sp, -8
    stw r12, 0(sp)
    stw r4, 4(sp)
    cmpw r3, r0
    bge print_positive
    addi r4, r3, 0
    li r3, MINUS_CHAR
    bl print_char
    sub r3, r0, r4

print_positive:
    bl print_int
    lwz r4, 4(sp)
    lwz r12, 0(sp)
    addi sp, sp, 8
    mtlr r12
    blr