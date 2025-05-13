#!/bin/bash

# 로그 디렉토리 생성
mkdir -p logs

# 기존 컨테이너 정리
docker-compose down

# 새 컨테이너 빌드 및 실행
docker-compose up -d --build

# 로그 설정
docker-compose logs -f > logs/container.log &

echo "서버가 백그라운드에서 실행 중입니다. 다음 명령어로 로그를 확인할 수 있습니다:"
echo "tail -f logs/container.log" 