# AWS Base Setup (EC2 + ECR)

이 문서는 Beyond News 백엔드를 EC2 + ECR + GitHub Actions로 배포하기 위한 최소 구성 가이드입니다.

## 1) ECR 리포지토리 생성

```bash
aws ecr create-repository --repository-name beyond-news-backend --region ap-northeast-2
```

## 2) EC2 생성 권장값

- AMI: Ubuntu 24.04 LTS
- 타입: t3.small (초기) / t3.micro(테스트용)
- 스토리지: 20GB 이상
- 보안그룹 인바운드:
  - 22: 본인 고정 IP만 허용
  - 80: 0.0.0.0/0
  - 443: 0.0.0.0/0 (HTTPS 적용 시)

EC2 생성 시 `infra/aws/user-data.sh`를 User Data로 넣으면 Docker/Compose가 자동 설치됩니다.

## 3) IAM Role

### GitHub Actions용 Role

- 정책: `infra/aws/iam-github-actions-policy.json`
- 용도: ECR 푸시
- 권장: OIDC 연동 (`token.actions.githubusercontent.com`)

### EC2 Instance Profile Role

- 정책: `infra/aws/iam-ec2-ecr-pull-policy.json`
- 용도: EC2에서 ECR 이미지 pull

## 4) EC2 배포 디렉토리 준비

```bash
sudo mkdir -p /opt/beyond-news
sudo chown -R ubuntu:ubuntu /opt/beyond-news
```

파일 배치 목표:

- `/opt/beyond-news/docker-compose.prod.yml`
- `/opt/beyond-news/scripts/deploy.sh`
- `/opt/beyond-news/.env`

## 5) GitHub Secrets

- `AWS_REGION`
- `AWS_ROLE_TO_ASSUME`
- `ECR_REPOSITORY`
- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_KEY`

## 6) 서버 런타임 .env 예시

```bash
AWS_REGION=ap-northeast-2
ECR_REGISTRY=123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
ECR_REPOSITORY=beyond-news-backend
IMAGE_TAG=latest
PORT=8000
HEALTHCHECK_URL=http://127.0.0.1:8000/health
```
