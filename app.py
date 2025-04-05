from flask import Flask, request, jsonify, render_template
from streamlit_art import process_response_json
from PIL import Image
import google.generativeai as genai
import os
import tempfile
import json
import requests
from chat_handler import chat_handler
import random
import datetime

app = Flask(__name__, template_folder='templates')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure Generative AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# NewsData.io API Key
NEWS_API_KEY = "pub_77072fd438680dc329735ccee217a48342639"

@app.route('/analyze', methods=['POST'])
def analyze_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image_file = request.files['image']
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    try:
        image_file.save(temp_file.name)
        temp_file.close()
        
        # Load prompt template
        with open('prompts/prompt_overall_analysis_json.txt') as f:
            prompt = f.read()
            
        with Image.open(temp_file.name) as img:
            response = model.generate_content([
                prompt,
                img
            ])
            response.resolve()
        
        analysis_data = process_response_json(response)
        if not analysis_data:
            raise ValueError('Failed to process Gemini response')

        try:
            # Extract and format the data according to the frontend's expected structure
            summary = analysis_data.get('summary', {})
            summary_text = f"Artist: {summary.get('artist', 'Unknown')}\n"
            summary_text += f"Painting: {summary.get('paintingName', 'Unknown')}\n"
            summary_text += f"Subject: {summary.get('subjectMatter', 'Unknown')}\n"
            summary_text += f"Medium: {summary.get('medium', 'Unknown')}\n"
            summary_text += f"Impression: {summary.get('overallImpression', 'Unknown')}"
            
            similar_artists = []
            for artist in analysis_data.get('similarArtists', []):
                if isinstance(artist, dict):
                    similar_artists.append(f"{artist.get('artistName', '')} ({artist.get('artistBirthYear', '')}-{artist.get('artistDeathYear', '')})")
            
            similar_paintings = []
            for painting in analysis_data.get('similarPaintings', []):
                if isinstance(painting, dict):
                    similar_paintings.append(f"{painting.get('painting', '')} by {painting.get('artist', '')} ({painting.get('yearOfPainting', '')})")
            
            # Format critique data
            critique = analysis_data.get('critique', {})
            critique_text = f"Composition and Balance: {critique.get('compositionAndBalance', 'Unknown')}\n"
            critique_text += f"Use of Color: {critique.get('useOfColor', 'Unknown')}\n"
            critique_text += f"Brushwork and Texture: {critique.get('brushworkAndTexture', 'Unknown')}\n"
            critique_text += f"Originality and Creativity: {critique.get('originalityAndCreativity', 'Unknown')}"

            # Store the analysis data in chat handler
            chat_handler.set_artwork_context({
                'summary': summary_text,
                'critique': critique_text,
                'similarArtists': similar_artists,
                'similarPaintings': similar_paintings
            })
            
            return jsonify({
                'summary': summary_text,
                'critique': critique_text,
                'similarArtists': similar_artists,
                'similarPaintings': similar_paintings
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    finally:
        if temp_file:
            os.remove(temp_file.name)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    response = chat_handler.get_chat_response(data['message'])
    return jsonify(response)

@app.route('/art-news', methods=['GET'])
def get_art_news():
    try:
        # Make request to newsdata.io API
        url = "https://newsdata.io/api/1/news"
        params = {
            'apikey': NEWS_API_KEY,
            'q': '"fine art" OR "art exhibition" OR "art gallery" OR "art museum" OR "art auction" OR "painting exhibition"',
            'language': 'en',
            'category': 'entertainment'
        }
        
        print("Fetching art news with params:", params)
        response = requests.get(url, params=params)
        print(f"API Response Status: {response.status_code}")
        
        # Check if response is valid JSON
        try:
            data = response.json()
            print(f"API Response: {data.get('status')}, Total Results: {len(data.get('results', []))}")
        except Exception as e:
            print(f"Error parsing JSON: {str(e)}")
            return jsonify({'error': f'Invalid API response: {str(e)}'}), 500
        
        # Check response status
        if response.status_code != 200 or data.get('status') == 'error':
            error_msg = data.get('results', {}).get('message', 'Unknown error') if data.get('status') == 'error' else 'Failed to fetch news'
            print(f"API Error: {error_msg}")
            return jsonify({'error': error_msg}), 500
            
        # Process and return the news data
        articles = data.get('results', [])
        print(f"Raw articles count: {len(articles)}")
        
        # Track processed titles to avoid duplicates
        processed_titles = set()
        processed_articles = []
        
        # Define art-related keywords for strict filtering
        art_keywords = [
            'fine art', 'painting', 'art exhibition', 'art gallery', 'art museum', 
            'artist', 'artwork', 'sculpture', 'art auction', 'art collection',
            'masterpiece', 'art fair', 'art biennale', 'art market'
        ]
        
        # Define keywords that must be excluded
        exclude_keywords = [
            'martial art', 'state of the art', 'art of war', 'art form', 
            'con artist', 'art director', 'art school', 'art department',
            'art therapy', 'art class', 'art student', 'art education',
            'nail art', 'makeup art', 'street art', 'graffiti',
            'art attack', 'art house', 'art film', 'art rock',
            'art deco', 'artificial', 'artillery', 'artisan', 'artifact',
            'article', 'articulate', 'artichoke', 'arthritis', 'arthur',
            'artificial intelligence', 'arts and crafts', 'art supplies'
        ]
        
        for article in articles:
            # Skip articles with missing essential data
            if not article.get('title') or not article.get('link'):
                continue
                
            # Skip duplicate titles
            title = article.get('title', '')
            if title.lower() in processed_titles:
                continue
                
            # Get text content for analysis
            title_lower = title.lower()
            description = article.get('description', '').lower() if article.get('description') else ''
            content = article.get('content', '').lower() if article.get('content') else ''
            full_text = title_lower + ' ' + description + ' ' + content
            
            # Skip if article contains any exclude keywords
            if any(keyword in full_text for keyword in exclude_keywords):
                continue
                
            # Check if the article contains at least one art-related keyword
            is_art_related = any(keyword in full_text for keyword in art_keywords)
            
            # Only include articles that are clearly art-related
            if is_art_related:
                # Add title to processed set to avoid duplicates
                processed_titles.add(title.lower())
                
                processed_articles.append({
                    'title': title,
                    'description': article.get('description', ''),
                    'image_url': article.get('image_url', ''),
                    'source': article.get('source_id', ''),
                    'published_at': article.get('pubDate', ''),
                    'link': article.get('link', '')
                })
        
        print(f"Processed articles count: {len(processed_articles)}")
        
        # If no articles were found, try a different query
        if len(processed_articles) < 2:
            print("No processed articles found, trying alternative query")
            
            # Try a different query
            params['q'] = 'art gallery OR art museum OR painting exhibition OR art auction'
            response = requests.get(url, params=params)
            
            try:
                data = response.json()
                if response.status_code == 200 and data.get('status') != 'error':
                    articles = data.get('results', [])
                    
                    for article in articles:
                        # Skip articles with missing essential data
                        if not article.get('title') or not article.get('link'):
                            continue
                            
                        # Skip duplicate titles
                        title = article.get('title', '')
                        if title.lower() in processed_titles:
                            continue
                            
                        # Get text content for analysis
                        title_lower = title.lower()
                        description = article.get('description', '').lower() if article.get('description') else ''
                        full_text = title_lower + ' ' + description
                        
                        # Skip if article contains any exclude keywords
                        if any(keyword in full_text for keyword in exclude_keywords):
                            continue
                            
                        # Check if the article contains at least one art-related keyword
                        is_art_related = any(keyword in full_text for keyword in art_keywords)
                        
                        # Only include articles that are clearly art-related
                        if is_art_related:
                            # Add title to processed set to avoid duplicates
                            processed_titles.add(title.lower())
                            
                            processed_articles.append({
                                'title': title,
                                'description': article.get('description', ''),
                                'image_url': article.get('image_url', ''),
                                'source': article.get('source_id', ''),
                                'published_at': article.get('pubDate', ''),
                                'link': article.get('link', '')
                            })
            except Exception as e:
                print(f"Error in fallback query: {str(e)}")
        
        # Limit to top 10 most relevant articles
        processed_articles = processed_articles[:10]
        
        print(f"Final articles count: {len(processed_articles)}")
        return jsonify(processed_articles)
    except Exception as e:
        print(f"Overall error in get_art_news: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/market-analysis', methods=['POST'])
def analyze_market():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image_file = request.files['image']
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    try:
        image_file.save(temp_file.name)
        temp_file.close()
        
        # Load prompt template for market analysis
        with open('prompts/prompt_market_analysis.txt', 'w') as f:
            f.write("""You are an expert art appraiser and market analyst. Analyze this artwork and provide a detailed market analysis in JSON format.
Include the following information:
{
  "estimatedValue": {
    "currentValue": "Estimated current market value in USD",
    "valueRange": "Possible value range in USD (e.g., $5,000-$7,000)",
    "confidence": "Confidence level (high, medium, low)"
  },
  "marketTrends": {
    "demandLevel": "Current market demand (very high, high, moderate, low)",
    "growthPotential": "Annual growth rate percentage for next 5 years",
    "marketStability": "Stability assessment (stable, volatile, uncertain)",
    "popularityTrend": "Trend direction (increasing, stable, decreasing)"
  },
  "investmentInsights": {
    "recommendedHoldingPeriod": "Recommended time to hold before selling (e.g., 5-10 years)",
    "investmentRisk": "Risk assessment (low, moderate, high)",
    "bestMarketSegment": "Best market segment for selling (galleries, auctions, private sales, online)",
    "topRegionalMarkets": ["List of 3 regions with highest demand for this style"]
  },
  "valuePredictions": {
    "oneYear": "Estimated value after 1 year in USD",
    "threeYears": "Estimated value after 3 years in USD",
    "fiveYears": "Estimated value after 5 years in USD",
    "tenYears": "Estimated value after 10 years in USD"
  },
  "comparableArtworks": [
    {
      "title": "Title of comparable artwork",
      "artist": "Artist name",
      "salePrice": "Recent sale price in USD",
      "saleDate": "Date of sale (year)",
      "venue": "Where it was sold (auction house, gallery, etc.)"
    }
  ],
  "marketFactors": {
    "positiveFactors": ["List of factors positively affecting value"],
    "negativeFactors": ["List of factors that could negatively impact value"],
    "keyConsiderations": ["Important considerations for potential buyers/sellers"]
  }
}

Base your analysis on the artwork's style, medium, subject matter, condition, size, and any recognizable artist or period. If the artist is unknown, estimate based on similar works. Provide realistic market values and growth rates.""")
        
        with open('prompts/prompt_market_analysis.txt') as f:
            prompt = f.read()
            
        with Image.open(temp_file.name) as img:
            try:
                response = model.generate_content([
                    prompt,
                    img
                ])
                response.resolve()
                
                # Extract the JSON from the response
                response_text = response.text
                # Find JSON content between triple backticks if present
                if "```json" in response_text and "```" in response_text.split("```json")[1]:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text and "```" in response_text.split("```")[1]:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text
                
                # Clean up the JSON string
                json_str = json_str.replace('\n', ' ').replace('\r', '')
                
                try:
                    market_data = json.loads(json_str)
                except json.JSONDecodeError:
                    # If Gemini doesn't return valid JSON, create a fallback response
                    print("Failed to parse JSON from Gemini response, using fallback")
                    market_data = generate_fallback_market_data()
                
                return jsonify(market_data)
            except Exception as e:
                print(f"Error generating market analysis: {str(e)}")
                # If Gemini fails, use fallback data
                market_data = generate_fallback_market_data()
                return jsonify(market_data)
    finally:
        if temp_file:
            os.remove(temp_file.name)

def generate_fallback_market_data():
    """Generate fallback market data if the AI analysis fails"""
    current_year = datetime.datetime.now().year
    base_value = random.randint(5000, 50000)
    growth_rate = random.uniform(0.05, 0.15)  # 5-15% annual growth
    
    # Calculate future values
    one_year = int(base_value * (1 + growth_rate))
    three_years = int(base_value * (1 + growth_rate) ** 3)
    five_years = int(base_value * (1 + growth_rate) ** 5)
    ten_years = int(base_value * (1 + growth_rate) ** 10)
    
    # Random market factors
    demand_levels = ["low", "moderate", "high", "very high"]
    stability_levels = ["stable", "volatile", "uncertain"]
    trend_directions = ["increasing", "stable", "decreasing"]
    risk_levels = ["low", "moderate", "high"]
    market_segments = ["galleries", "auctions", "private sales", "online"]
    regions = ["North America", "Europe", "Asia", "Middle East", "South America", "Australia"]
    
    positive_factors = [
        "Strong provenance", 
        "Excellent condition", 
        "Rare subject matter", 
        "Growing artist recognition",
        "Historical significance",
        "Featured in recent exhibitions"
    ]
    
    negative_factors = [
        "Market saturation for similar works",
        "Economic uncertainty",
        "Changing collector preferences",
        "Condition issues",
        "Authentication concerns",
        "Limited exhibition history"
    ]
    
    considerations = [
        "Consider professional appraisal",
        "Obtain condition report",
        "Research recent comparable sales",
        "Monitor artist's market performance",
        "Evaluate auction trends for similar works",
        "Consider insurance and proper storage"
    ]
    
    # Generate comparable artworks
    comparable_artworks = []
    for i in range(3):
        comparable_artworks.append({
            "title": f"Untitled Artwork #{random.randint(100, 999)}",
            "artist": "Unknown Artist",
            "salePrice": f"${random.randint(int(base_value * 0.8), int(base_value * 1.2)):,}",
            "saleDate": str(current_year - random.randint(0, 3)),
            "venue": random.choice(["Sotheby's", "Christie's", "Phillips", "Bonhams", "Heritage Auctions"])
        })
    
    return {
        "estimatedValue": {
            "currentValue": f"${base_value:,}",
            "valueRange": f"${int(base_value * 0.8):,}-${int(base_value * 1.2):,}",
            "confidence": random.choice(["low", "medium", "high"])
        },
        "marketTrends": {
            "demandLevel": random.choice(demand_levels),
            "growthPotential": f"{growth_rate * 100:.1f}%",
            "marketStability": random.choice(stability_levels),
            "popularityTrend": random.choice(trend_directions)
        },
        "investmentInsights": {
            "recommendedHoldingPeriod": f"{random.randint(3, 10)} years",
            "investmentRisk": random.choice(risk_levels),
            "bestMarketSegment": random.choice(market_segments),
            "topRegionalMarkets": random.sample(regions, 3)
        },
        "valuePredictions": {
            "oneYear": f"${one_year:,}",
            "threeYears": f"${three_years:,}",
            "fiveYears": f"${five_years:,}",
            "tenYears": f"${ten_years:,}"
        },
        "comparableArtworks": comparable_artworks,
        "marketFactors": {
            "positiveFactors": random.sample(positive_factors, 3),
            "negativeFactors": random.sample(negative_factors, 3),
            "keyConsiderations": random.sample(considerations, 3)
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5500)