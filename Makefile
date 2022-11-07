diagram: diagram.xopp
	xournalpp -p diagram.pdf diagram.xopp
	git add diagram.xopp
	git add diagram.pdf
	git commit -m "update diagram"
	git push
	git pull