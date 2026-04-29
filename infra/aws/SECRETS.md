# GitHub Secrets and Security Checklist

## Required GitHub Secrets

- `AWS_REGION` (예: `ap-northeast-2`)
- `AWS_ROLE_TO_ASSUME` (GitHub OIDC로 Assume할 IAM Role ARN)
- `ECR_REPOSITORY` (예: `beyond-news-backend`)
- `EC2_HOST` (공인 IP 또는 도메인)
- `EC2_USER` (예: `ubuntu`)
- `EC2_SSH_KEY` (PEM 개인키 내용)

## EC2 .env Required Keys

- `AWS_REGION`
- `ECR_REGISTRY` (예: `123456789012.dkr.ecr.ap-northeast-2.amazonaws.com`)
- `ECR_REPOSITORY`
- `IMAGE_TAG` (초기값 `latest`)
- `PORT` (기본 `8000`)
- `HEALTHCHECK_URL` (기본 `http://127.0.0.1:8000/health`)

## Hardening Checklist

- IAM 최소권한 사용 (`infra/aws/iam-github-actions-policy.json`, `infra/aws/iam-ec2-ecr-pull-policy.json`)
- GitHub Actions Role은 OIDC 기반 Assume Role만 허용
- Trust policy의 `sub`를 `main` 브랜치로 제한
- 보안그룹 22번 포트는 고정 IP만 허용
- EC2에 SSH 비밀번호 로그인 비활성화
- `.env`, 키 파일은 Git에 커밋 금지
