# Multi-Strategy Options Scanner Pro

## ✅ **PROJECT COMPLETE - ALL 8 STRATEGIES IMPLEMENTED!** 🎉

**Status**: 🟢 RUNNING on http://127.0.0.1:5002  
**Strategies**: 8/8 Implemented and Tested  
**Completed**: November 15, 2025

A comprehensive options strategy scanner supporting 8 different strategies with real-time data from Alpha Vantage, advanced filtering, and interactive payoff visualizations.

## 🎯 Supported Strategies

1. **PMCC** - Poor Man's Covered Call (Bullish)
2. **PMCP** - Poor Man's Covered Put (Bearish)
3. **Synthetic Long** - Long Call + Short Put (Bullish)
4. **Synthetic Short** - Short Call + Long Put (Bearish)
5. **Jade Lizard** - Short Put + Call Spread (Neutral/Bullish, No upside risk)
6. **Twisted Sister** - Short Call + Put Spread (Neutral/Bearish, No downside risk)
7. **Broken Wing Butterfly (Put)** - Asymmetric butterfly (Bullish)
8. **Broken Wing Butterfly (Call)** - Asymmetric butterfly (Bearish)

## 🏗️ Project Structure

```
multi-strategy-scanner/
├── backend/
│   ├── app.py                    # Main Flask application
│   ├── config.py                 # Configuration
│   ├── requirements.txt          # Python dependencies
│   ├── strategies/               # Strategy implementations
│   ├── utils/                    # Utility functions
│   └── database/                 # Database layer
├── frontend/
│   ├── templates/                # HTML templates
│   └── static/                   # CSS, JS, assets
└── docs/                         # Documentation
```

## 📋 Features

- ✅ Real-time options data from Alpha Vantage API
- ✅ Advanced filtering with custom criteria
- ✅ Interactive payoff diagrams using Plotly.js
- ✅ PostgreSQL database for persistence
- ✅ Favorites management
- ✅ Strategy comparison tools
- ✅ ROC, POP, and Greeks calculations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Alpha Vantage API key

### Installation

1. **Clone and navigate to project:**
   ```bash
   cd multi-strategy-scanner
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp backend/.env.example backend/.env
   # Edit .env with your credentials
   ```

5. **Set up database:**
   ```bash
   psql -U your_user -d your_database -f backend/database/schema.sql
   ```

6. **Run the application:**
   ```bash
   cd backend
   python app.py
   ```

7. **Access the app:**
   Open browser to `http://localhost:5000`

## 🔧 Configuration

Edit `backend/.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/your_database
ALPHAVANTAGE_API_KEY=your_api_key_here
FLASK_ENV=development
FLASK_DEBUG=1
PORT=5000
```

## 📊 Database Schema

The application uses tables prefixed with `ms_` (multi-strategy):
- `ms_filter_criteria` - Saved filter configurations
- `ms_scan_results` - Historical scan results
- `ms_favorites` - Favorite positions
- `ms_strategies` - Strategy metadata

**Note:** These tables are isolated and will not interfere with any existing `strategy_*` tables.

## 🎨 Usage

### Scanner Tab
1. Select strategy from dropdown
2. Enter symbols (comma-separated)
3. Choose saved filter or use current settings
4. Click "Scan Opportunities"
5. View results with key metrics
6. Click "View Payoff" to see interactive chart

### Filter Criteria Tab
1. Enter filter name
2. Select strategy type
3. Configure strategy-specific parameters
4. Save filter for future use

### Favorites Tab
1. Browse saved opportunities
2. Sort by ROC, POP, or date
3. Filter by strategy or symbol
4. View payoff diagrams
5. Add notes and tags

## 🔌 API Endpoints

```
GET  /api/strategies              - List all strategies
GET  /api/filters                 - List saved filters
POST /api/filters                 - Create new filter
POST /api/scan                    - Run strategy scan
GET  /api/favorites               - List favorites
POST /api/favorites               - Add to favorites
GET  /api/payoff/<strategy>       - Calculate payoff data
```

## 🧪 Testing

```bash
cd backend
python -m pytest tests/
```

## 📦 Deployment

### Heroku Deployment

1. **Create Heroku app:**
   ```bash
   heroku create your-app-name
   ```

2. **Add PostgreSQL:**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

3. **Set environment variables:**
   ```bash
   heroku config:set ALPHAVANTAGE_API_KEY=your_key
   ```

4. **Deploy:**
   ```bash
   git push heroku main
   ```

5. **Initialize database:**
   ```bash
   heroku pg:psql < backend/database/schema.sql
   ```

## 📚 Documentation

- [Strategy Guide](docs/STRATEGY_GUIDE.md) - Detailed strategy explanations
- [API Documentation](docs/API_DOCUMENTATION.md) - Complete API reference
- [User Manual](docs/USER_MANUAL.md) - End-user guide

## 🤝 Contributing

This is a private project. For issues or suggestions, contact the maintainer.

## 📄 License

Private/Proprietary

## 🙏 Acknowledgments

- Options strategies tested in `Options-Analysis-Strategies.ipynb`
- Architecture inspired by `options-scanner-v2` project
- Alpha Vantage for real-time options data

---

**Built with ❤️ for professional options trading analysis**
