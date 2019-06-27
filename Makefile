PROJECT_REPO=arcusplatformnet
VERSION=0.1.0

build:
	docker build -t ${PROJECT_REPO}/duckling:${VERSION} services/duckling
	docker build -t ${PROJECT_REPO}/arcusservice:${VERSION} services/asm
	docker build -t ${PROJECT_REPO}/ngix:${VERSION} services/nginx

push:
    docker push ${PROJECT_REPO}/arcusservice:${VERSION}