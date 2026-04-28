echo "DEFAULT_ADMIN_EMAIL=admin@aura.com" >> /home/ubuntu/aura-prod/backend/.env
echo "DEFAULT_ADMIN_PASSWORD=adminpassword" >> /home/ubuntu/aura-prod/backend/.env
cd /home/ubuntu/aura-prod
docker compose -f docker-compose.prod.yml up -d
