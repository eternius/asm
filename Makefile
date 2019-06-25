PROJECT_REPO=eternius
VERSION=latest

build:
	docker build -t ${PROJECT_REPO}/duckling:${VERSION} services/duckling
	docker build -t ${PROJECT_REPO}/arcusservice:${VERSION} services/asm
	docker build -t ${PROJECT_REPO}/ngix:${VERSION} services/nginx

push:
    docker push ${PROJECT_REPO}/arcusservice:${VERSION}