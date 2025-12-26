# Multi-Strategy Options Scanner - Heroku Deployment

## Prerequisites

1. **Heroku Account**: Sign up at [heroku.com](https://heroku.com)
2. **Heroku CLI**: Install from [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)
3. **Git**: Ensure git is installed and repository is initialized
4. **Alpha Vantage API Key**: Get free key from [alphavantage.co](https://www.alphavantage.co/support/#api-key)

## Quick Deploy to Heroku

### Option 1: Deploy via Heroku Button

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

Click the button above and follow the prompts in your browser.

### Option 2: Deploy via Heroku CLI

1. **Login to Heroku**
   ```bash
   heroku login
   ```

2. **Create a New Heroku App**
   ```bash
   heroku create your-app-name
   ```
   Or let Heroku generate a name:
   ```bash
   heroku create
   ```

3. **Add PostgreSQL Database**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

4. **Set Environment Variables**
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set FLASK_DEBUG=False
   heroku config:set SECRET_KEY=$(openssl rand -base64 32)
   heroku config:set ALPHAVANTAGE_API_KEY=your_api_key_here
   ```

5. **Deploy the Application**
   ```bash
   git push heroku main
   ```
   Or if your branch is named differently:
   ```bash
   git push heroku your-branch-name:main
   ```

6. **Initialize the Database**
   ```bash
   heroku run python backend/database/init_db.py
   ```

7. **Open Your App**
   ```bash
   heroku open
   ```

## Configuration

### Environment Variables

Set these in Heroku Dashboard → Settings → Config Vars:

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `FLASK_ENV` | Yes | Environment (production/development) | production |
| `SECRET_KEY` | Yes | Flask session secret (auto-generated) | - |
| `DATABASE_URL` | Yes | PostgreSQL connection (auto-set by addon) | - |
| `ALPHAVANTAGE_API_KEY` | Yes | Alpha Vantage API key | - |
| `FLASK_DEBUG` | No | Enable debug mode | False |
| `MAX_SYMBOLS_PER_SCAN` | No | Max symbols per scan | 10 |
| `ENABLE_RATE_LIMITING` | No | Enable rate limiting | True |
| `RATE_LIMIT_PER_MINUTE` | No | API rate limit | 60 |

### Viewing Environment Variables
```bash
heroku config
```

### Setting Environment Variables
```bash
heroku config:set VARIABLE_NAME=value
```

## Database Management

### Run Database Migrations
```bash
heroku run python backend/database/init_db.py
```

### Access PostgreSQL Database
```bash
heroku pg:psql
```

### Database Backups
```bash
# Create backup
heroku pg:backups:capture

# List backups
heroku pg:backups

# Download backup
heroku pg:backups:download
```

## Monitoring

### View Logs
```bash
# Real-time logs
heroku logs --tail

# Last 200 lines
heroku logs -n 200

# Filter by source
heroku logs --source app --tail
```

### Application Metrics
```bash
heroku ps
```

## Scaling

### Scale Dynos
```bash
# Scale web dynos
heroku ps:scale web=1

# Scale to multiple dynos (requires paid plan)
heroku ps:scale web=2
```

### Change Dyno Type
```bash
# Upgrade to standard dyno
heroku ps:type web=standard-1x

# Upgrade to performance dyno
heroku ps:type web=performance-m
```

## Troubleshooting

### App Won't Start
```bash
# Check logs
heroku logs --tail

# Check dyno status
heroku ps

# Restart app
heroku restart
```

### Database Connection Issues
```bash
# Check DATABASE_URL is set
heroku config:get DATABASE_URL

# Check database status
heroku pg:info

# Restart database
heroku pg:restart
```

### Port Issues
The app automatically uses Heroku's `$PORT` environment variable. No configuration needed.

## Local Development vs Production

### Local Development
```bash
# Use .env file
cp backend/.env.example backend/.env

# Run locally
cd backend
python app.py
```

### Production (Heroku)
- Uses Config Vars instead of .env file
- `FLASK_ENV=production`
- `FLASK_DEBUG=False`
- Gunicorn as WSGI server
- PostgreSQL database

## Maintenance

### Update Application
```bash
# Make changes
git add .
git commit -m "Update message"

# Deploy
git push heroku main
```

### Restart Application
```bash
heroku restart
```

### View Application Info
```bash
heroku info
```

## Cost Estimation

### Free Tier
- **Dynos**: 550-1000 free dyno hours/month
- **Database**: 10,000 rows (mini plan)
- **Limitations**: Apps sleep after 30 min of inactivity

### Paid Plans
- **Basic**: $7/month (no sleeping)
- **Standard**: $25-50/month (more memory/CPU)
- **PostgreSQL Mini**: $5/month (10M rows)

## Security Best Practices

1. **Never commit .env files** - Use Config Vars
2. **Use strong SECRET_KEY** - Auto-generated during setup
3. **Enable HTTPS** - Automatic on Heroku
4. **Rotate API keys** - Periodically update ALPHAVANTAGE_API_KEY
5. **Limit CORS origins** - Set CORS_ORIGINS to specific domains

## Support

For Heroku-specific issues:
- [Heroku Dev Center](https://devcenter.heroku.com/)
- [Heroku Status](https://status.heroku.com/)

For application issues:
- Check application logs: `heroku logs --tail`
- Review documentation in repository

## Next Steps

After deployment:
1. ✅ Test all strategy scans
2. ✅ Verify database connections
3. ✅ Test P&L diagram functionality
4. ✅ Configure rate limiting
5. ✅ Set up monitoring/alerts
6. ✅ Consider custom domain (requires paid dyno)
