@echo off
REM Remove common LaTeX auxiliary files from this repository.
REM This does not remove .tex, .bib, images, or website source files.
for /r %%F in (*.aux *.bbl *.blg *.idx *.ilg *.ind *.lof *.log *.lot *.out *.toc *.synctex.gz *.fls *.fdb_latexmk *.bcf *.run.xml) do del /q "%%F"
if exist site rmdir /s /q site
if exist lateximages rmdir /s /q lateximages
if exist Axiomathic-images rmdir /s /q Axiomathic-images
if exist site.css del /q site.css
if exist lwarp.css del /q lwarp.css
if exist web\site-config.json del /q web\site-config.json
