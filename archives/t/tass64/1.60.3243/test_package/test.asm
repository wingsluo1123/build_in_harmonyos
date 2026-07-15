; Simple 6502 test program for 64tass
; Assembles a basic LDA/STA loop
*=$0801
main:
    lda #$00
    sta $d020
    rts
