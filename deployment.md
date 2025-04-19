# Deployment Instructions

## Prerequisites
1. Python 3.8+
2. MySQL 8.0+
3. Nginx
4. Let's Encrypt SSL certificate
5. Domain name pointing to your server

## Server Setup
1. Install required packages:
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx mysql-server supervisor
```

2. Create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.production .env
# Edit .env with your production values
```

4. Set up the database:
```bash
mysql -u root -p
CREATE DATABASE hoto CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'hoto_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON hoto.* TO 'hoto_user'@'localhost';
FLUSH PRIVILEGES;
```

5. Initialize the application:
```bash
python manage.py collectstatic
python manage.py migrate
python manage.py create_admin
```

6. Set up Nginx and SSL:
```bash
sudo ln -s /etc/nginx/sites-available/hoto /etc/nginx/sites-enabled/
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
sudo systemctl restart nginx
```

7. Start the application:
```bash
sudo systemctl start hoto
sudo systemctl enable hoto
```

## Maintenance
- Monitor logs: `tail -f /var/log/gunicorn/error.log`
- Restart application: `sudo systemctl restart hoto`
- Update application:
```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart hoto
```