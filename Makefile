PROJECT_REPO=st3images
VERSION=3.1dev

build:
	docker build -t ${PROJECT_REPO}/st3reactor:${VERSION} .

push:
    docker push ${PROJECT_REPO}/st3reactor:${VERSION}