# AiArtCritiqueBot - AI Art Analysis & Market Intelligence Platform

A sophisticated AI-powered platform for art analysis, critique, and market intelligence. This application leverages Google's Generative AI to provide detailed artwork analysis, market valuations, and real-time art news, helping art enthusiasts, collectors, and professionals make informed decisions.

## 🎨 Features

### Art Analysis
- **AI-Powered Art Critique**: Detailed analysis of composition, color usage, and artistic techniques
- **Artist Recognition**: Identify artists and artistic styles
- **Similar Artwork Discovery**: Find related artworks and artists
- **Technical Analysis**: Evaluate brushwork, texture, and artistic elements

### Market Intelligence
- **Real-time Art Market News**: Stay updated with the latest art market trends
- **Value Estimation**: AI-driven artwork valuation and price predictions
- **Market Trend Analysis**: Track market demand and investment potential
- **Comparable Sales**: Access data on similar artwork transactions

### Interactive Features
- **AI Chat Assistant**: Get personalized insights about artworks
- **Portfolio Analysis**: Track and analyze art collections
- **Market Reports**: Generate detailed market analysis reports
- **News Integration**: Curated art news from reliable sources

## 🛠️ Technologies

### Backend
- **Flask**: Python web framework for the application server
- **Google Generative AI**: Advanced AI model for artwork analysis
- **PIL (Python Imaging Library)**: Image processing capabilities
- **NewsData.io API**: Real-time art market news integration

### Frontend
- **HTML/CSS/JavaScript**: Responsive user interface
- **Fetch API**: Asynchronous data handling
- **Custom UI Components**: Interactive analysis display

## 📋 Prerequisites

- Python 3.8 or higher
- pip package manager
- Google Generative AI API key
- NewsData.io API key

## 🔧 Installation

1. Clone the repository
```bash
git clone https://github.com/Kamakshi0101/finalai2.git
```

2. Create and activate virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
Create a `.env` file in the root directory with:
```env
GEMINI_API_KEY=your_gemini_api_key
NEWS_API_KEY=your_newsdata_api_key
```

5. Start the application
```bash
python app.py
```

6. Open your browser and navigate to `http://localhost:5500`

## 🚀 Usage

### Analyzing Artwork
1. Upload an image of the artwork you want to analyze
2. Receive detailed AI analysis including:
   - Artistic style and technique analysis
   - Similar artists and artworks
   - Market value estimation
   - Investment potential

### Market Analysis
- View real-time art market trends
- Access detailed price predictions
- Explore comparable artwork sales
- Track market factors affecting value

### News Integration
- Browse curated art market news
- Filter news by relevance and impact
- Track market sentiment

## 📁 Project Structure
```
/
├── app.py                 # Main application file
├── chat_handler.py        # AI chat functionality       
├── templates/             # HTML templates
├── prompts/               # AI prompt templates
├── examples/              # Example artworks
└── requirements.txt       # Project dependencies
```

## 🔄 API Integrations

- **Google Generative AI**: Powers the artwork analysis and chat features
- **NewsData.io**: Provides real-time art market news and updates

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

If you encounter any issues or have questions, please file an issue on the GitHub repository.

## ⚠️ Disclaimer

This application's art analysis and market valuations are for informational purposes only and should not be considered as professional appraisals. Always consult with qualified art experts for official valuations and authentication.

# finalai2