PROJECT_REPO=eternius
VERSION=latest

build:
	docker build -t ${PROJECT_REPO}/arcusservice:${VERSION} .

push:
    docker push ${PROJECT_REPO}/arcusservice:${VERSION}