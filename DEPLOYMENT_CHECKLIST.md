# Heroku Deployment Checklist

## Pre-Deployment Checklist

- [ ] **Heroku CLI Installed** - Download from https://devcenter.heroku.com/articles/heroku-cli
- [ ] **Git Repository Initialized** - Run `git init` if needed
- [ ] **Alpha Vantage API Key** - Get free key from https://www.alphavantage.co/support/#api-key
- [ ] **Code Committed** - All changes committed to git
- [ ] **Dependencies Updated** - `requirements.txt` is up to date

## Files Created for Heroku

✅ **Procfile** - Defines how to run the app on Heroku
✅ **runtime.txt** - Specifies Python version (3.11.9)
✅ **requirements.txt** - Lists all Python dependencies
✅ **app.json** - Heroku app configuration
✅ **.gitignore** - Prevents sensitive files from being committed
✅ **HEROKU_DEPLOY.md** - Detailed deployment instructions
✅ **deploy-heroku.sh** - Automated deployment script

## Configuration Updates

✅ **config.py** - Updated to handle Heroku's DATABASE_URL format
✅ **app.py** - Uses PORT from environment variable
✅ **Gunicorn** - Already in requirements.txt for production server

## Deployment Steps

### Option 1: Automated Script
```bash
./deploy-heroku.sh
```

### Option 2: Manual Deployment
```bash
# 1. Login
heroku login

# 2. Create app
heroku create your-app-name

# 3. Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# 4. Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=$(openssl rand -base64 32)
heroku config:set ALPHAVANTAGE_API_KEY=your_api_key_here

# 5. Deploy
git push heroku main

# 6. Initialize database
heroku run python backend/database/init_db.py

# 7. Open app
heroku open
```

## Post-Deployment Verification

- [ ] **App Accessible** - Visit your Heroku URL
- [ ] **Database Connected** - Check `heroku pg:info`
- [ ] **Strategies Load** - Test PMCC scan with AAPL
- [ ] **API Working** - Test all strategy scans
- [ ] **P&L Diagram** - Verify diagram renders correctly
- [ ] **Logs Clean** - Check `heroku logs --tail` for errors

## Environment Variables to Set

| Variable | Example Value | Required |
|----------|---------------|----------|
| `FLASK_ENV` | production | ✅ |
| `SECRET_KEY` | (auto-generated) | ✅ |
| `DATABASE_URL` | (auto-set by addon) | ✅ |
| `ALPHAVANTAGE_API_KEY` | YOUR_KEY_HERE | ✅ |
| `FLASK_DEBUG` | False | ⚠️ |
| `MAX_SYMBOLS_PER_SCAN` | 10 | ❌ |
| `ENABLE_RATE_LIMITING` | True | ❌ |

## Common Issues & Solutions

### Issue: "Application Error" on Heroku
**Solution**: Check logs with `heroku logs --tail`

### Issue: Database connection fails
**Solution**: 
```bash
heroku config:get DATABASE_URL
heroku pg:info
heroku run python backend/database/init_db.py
```

### Issue: Port binding error
**Solution**: Ensure app.py uses `os.getenv('PORT', 5000)` ✅ Already done

### Issue: Missing dependencies
**Solution**: 
```bash
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update requirements"
git push heroku main
```

## Monitoring Commands

```bash
# View logs
heroku logs --tail

# Check dyno status
heroku ps

# View app info
heroku info

# Check database
heroku pg:info

# View config vars
heroku config

# Restart app
heroku restart
```

## Scaling (if needed)

```bash
# Scale to 2 dynos (requires paid plan)
heroku ps:scale web=2

# Upgrade dyno type
heroku ps:type web=standard-1x
```

## Cost Summary

### Free Tier
- 550-1000 free dyno hours/month
- App sleeps after 30 min inactivity
- 10,000 database rows

### Upgrade Options
- **Basic Plan**: $7/month (no sleeping)
- **Standard Plan**: $25/month (more resources)
- **PostgreSQL Mini**: $5/month (10M rows)

## Next Steps After Deployment

1. ✅ Test all 8 strategies (PMCC, PMCP, Synthetic Long/Short, Jade Lizard, Twisted Sister, BWB Put/Call)
2. ✅ Verify P&L diagram with inflection points
3. ✅ Test accordion UI with multiple results
4. ✅ Check database persistence
5. ✅ Monitor Alpha Vantage API usage
6. 🔧 Consider custom domain (requires paid dyno)
7. 🔧 Set up monitoring/alerts
8. 🔧 Configure CI/CD pipeline (optional)

## Support Resources

- **Heroku Docs**: https://devcenter.heroku.com/
- **Deployment Guide**: See HEROKU_DEPLOY.md
- **Logs**: `heroku logs --tail`
- **Status**: https://status.heroku.com/
