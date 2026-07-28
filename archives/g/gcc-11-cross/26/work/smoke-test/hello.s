	.arch armv8-a+crc
	.file	"hello.c"
	.text
	.align	2
	.global	main
	.type	main, %function
main:
.LFB0:
	mov	w0, 0
	ret
.LFE0:
	.size	main, .-main
	.section	.eh_frame,"aw",@progbits
.Lframe1:
	.4byte	.LECIE1-.LSCIE1
.LSCIE1:
	.4byte	0
	.byte	0x3
	.string	"zR"
	.byte	0x1
	.byte	0x78
	.byte	0x1e
	.byte	0x1
	.byte	0x1b
	.byte	0xc
	.byte	0x1f
	.byte	0
	.align	3
.LECIE1:
.LSFDE1:
	.4byte	.LEFDE1-.LASFDE1
.LASFDE1:
	.4byte	.LASFDE1-.Lframe1
	.4byte	.LFB0-.
	.4byte	.LFE0-.LFB0
	.byte	0
	.align	3
.LEFDE1:
	.ident	"GCC: (GNU) 11.5.0"
	.section	.note.GNU-stack,"",@progbits
