# Poppler PDF Library

> PDF rendering library based on xpdf, for PDF document manipulation

## 简介

Poppler is a PDF rendering library based on Xpdf 3.0. It provides tools for PDF document processing, including:
- `pdfattach`: Attach files to PDF
- `pdfdetach`: Extract attachments from PDF
- `pdffonts`: List fonts used in PDF
- `pdfimages`: Extract images from PDF
- `pdfinfo`: Display PDF document info
- `pdftohtml`: Convert PDF to HTML
- `pdftoppm`: Convert PDF to PPM images
- `pdftops`: Convert PDF to PostScript
- `pdftotext`: Extract text from PDF
- `pdfseparate`: Extract pages from PDF
- `pdfunite`: Merge PDF pages

## OHOS 适配要点

1. Requires fontconfig for font rendering
2. Depends on openjpeg for JPEG2000 image support
3. Binary tools may have ELF signature issues on HarmonyOS

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| fontconfig | 2.15.0 | Font configuration |
| openjpeg | 2.5.2 | JPEG2000 support |
| libiconv | 1.17 | Character encoding conversion |
| openssl | 3.3.1 | TLS support |

## 功能验证

```bash
pdfinfo --version
pdftotext input.pdf output.txt
```

## 参考

- [官方文档](https://poppler.freedesktop.org/)
- [源码仓库](https://gitlab.freedesktop.org/poppler/poppler)