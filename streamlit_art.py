import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os
import pathlib
from pathlib import Path
import logging
import numpy as np
import pandas as pd
import time
import base64
import requests
import json
import sys
import re
import version
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logger
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

# Debug mode
DEBUG = False

# Save JSON response for testing
SAVE_JSON = False

# If LoadLocalJSON is enabled, load OpenAI JSON responses from disk
LOAD_LOCAL_JSON = False

# Load from GEMINI_API_KEY env variable, otherwise allow users to set their own Gemini API Key
def get_gemini_api_key():
    # Loading Gemini API Key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Loading Gemini API Key from user input
        api_key = st.text_input("Enter your Gemini API key:")

    return api_key

def save_image_to_temp(uploaded_file):
    buffer = uploaded_file.getbuffer()
    with open(os.path.join("/tmp/",uploaded_file.name),"wb") as f:
        f.write(buffer)

def get_image_base64(uploaded_file):
    return base64.b64encode(uploaded_file.getbuffer()).decode('utf-8')


def save_response_json(response_json, filename):
    # Save to file 
    with open(filename, 'w') as f:
        json.dump(response_json, f)

def load_response_json(filename):
    # Load from file 
    with open(filename) as f:
        data = json.load(f)
        return data

# Extract only the valid JSON portion from a long string containing JSON and other text
def extract_json(data):
  decoder = json.JSONDecoder()
  pos = 0
  json_str = ""

  while pos < len(data):
    try:
      result, idx = decoder.raw_decode(data[pos:])
      json_str += data[pos:pos+idx]
      return json.dumps(result)
    except json.decoder.JSONDecodeError:
      pos += 1

  return None

def is_valid_json(string):
    try:
        json_object = re.match(
            r'^{"[^"]*":[^,]*,?}$', string
        )
    except:
        return False

    if not json_object:
        try:
            json_array = re.match(
                r'^\[[^\]]*\]$', string
            )
        except:
            return False

    if json_object or json_array:
        return True
    else:
        return False

def process_response_json(response):
    # Process Gemini's response
    if not response or not hasattr(response, 'text'):
        LOGGER.error("Invalid or empty response from Gemini API")
        return None

    try:
        # Extract the text content from Gemini's response
        content = response.text.strip()
        
        if not content:
            LOGGER.error("Empty content in Gemini response")
            return None

        # Try to extract JSON from the response if it's wrapped in markdown code blocks
        if '```json' in content:
            # Split by ```json and take the content after it
            parts = content.split('```json')
            if len(parts) < 2:
                LOGGER.error("Malformed JSON block in response")
                return None
            # Take the content after ```json and before the next ```
            json_content = parts[1].split('```')[0].strip()
            if not json_content:
                LOGGER.error("Empty JSON content in code block")
                return None
            content = json_content
        
        # Parse the JSON content
        try:
            response_obj = json.loads(content)
            if not isinstance(response_obj, dict):
                LOGGER.error("Response is not a valid JSON object")
                return None
            return response_obj
        except json.JSONDecodeError as je:
            LOGGER.error(f"JSON decode error: {str(je)}")
            # Try to clean the content and parse again
            cleaned_content = content.replace('\\n', '\n').replace('\\"', '"')
            try:
                response_obj = json.loads(cleaned_content)
                return response_obj
            except:
                LOGGER.error("Failed to parse JSON even after cleaning")
                return None
    except Exception as e:
        LOGGER.error("Error processing Gemini response", exc_info=True)
        st.error(f"Error processing response: {str(e)}")
        return None

# See: https://platform.openai.com/docs/guides/vision
def analyze_image(uploaded_file, api_key):
    # Configure Gemini API
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        st.error(f"Error configuring Gemini model: {str(e)}")
        return None

    # Load prompt from file
    with open('prompts/prompt_overall_analysis_json.txt') as f: prompt = f.read()

    # Convert uploaded file to PIL Image and get base64 encoding
    image = Image.open(uploaded_file)
    image_base64 = get_image_base64(uploaded_file)

    # Prepare request content
    content = [
        {"text": prompt},
        {"inline_data": {
            "mime_type": "image/jpeg",
            "data": image_base64
        }}
    ]

    # Generate response from Gemini
    with st.spinner('Analyzing image with Gemini...'):
        response = model.generate_content(content)
        response.resolve()

    # Sample Response - Chat GPT Completion JSON with choices[0]->messages->content encoded ad JSON
    # {
    #   "id": "chatcmpl-8RTetTTSJfwM2Xmm8mTPfwZlL5mDR",
    #   "object": "chat.completion",
    #   "created": 1701559555,
    #   "model": "gpt-4-1106-vision-preview",
    #   "usage": {
    #     "prompt_tokens": 1032,
    #     "completion_tokens": 578,
    #     "total_tokens": 1610
    #   },
    #   "choices": [
    #     {
    #       "message": {
    #         "role": "assistant",
    #         "content": "```json\n{\n  \"Artwork_Summary\":

    try:
        # Process the response
        response_obj = process_response_json(response)
        
        if SAVE_JSON and response_obj:
            save_response_json(response_obj, "debug/response.json")
            
        return response_obj
        
    except Exception as e:
        LOGGER.error("Error processing Gemini response", exc_info=True)
        st.error(f"Error analyzing image: {str(e)}")
        return None

def process_hex_colors(data):
    """
    Process the nested dictionary to extract area and color information.
    """
    processed_data = []

    for key, value in data.items():
        if isinstance(value, list):
            # Direct list of colors

            # Add styling
            def process_value(item):
                item = '<span style="color:' + item + '">&block;</span> ' + item
                return item

            # Process each value inline
            updated_value = [process_value(item) for item in value] 

            processed_data.append([key.capitalize(), ", ".join(updated_value)])
        elif isinstance(value, dict):
            # Nested dictionary
            for subkey, subvalue in value.items():
                area_name = f"{key.capitalize()} ({subkey})"
                colors = ", ".join(subvalue)
                processed_data.append([area_name, colors])

    return processed_data


def render_results(response_obj):

    if DEBUG:
        st.write("Response Object = ", response_obj)

    if response_obj == None:
        raise Exception("No response from OpenAI API, Response object is None")

    if "error" in response_obj:
        st.error("OpenAI Error: " + response_obj["error"])
        raise Exception("OpenAI API error: ", response_obj["error"])

    tab_titles = ["Summary", "Critique", "Composition", "Similar Artists", "Similar Paintings"]

    if DEBUG:
        tab_titles.append("JSON Output")
    
    tabs = st.tabs(tab_titles)
    empty_value = "Unknown"

    # Summary Tab
    with tabs[0]:

        st.header("Summary")

        if "summary" not in response_obj:
            st.write("No summary data found")

        else:
            summary=response_obj["summary"]

            st.subheader("Artist")
            st.write(summary.get("artist", empty_value))

            st.subheader("Painting Name")
            st.write(summary.get("paintingName", empty_value))

            st.subheader("Subject Matter")
            st.write(summary.get("subjectMatter", empty_value))

            st.subheader("Medium")
            st.write(summary.get("medium", empty_value))

            st.subheader("Overall Impression")
            st.write(summary.get("overallImpression", empty_value))

    # Critique Tab
    with tabs[1]:

        st.header("Critique")

        if "critique" not in response_obj:
            st.write("No critique data found")

        else:

            critique=response_obj["critique"]

            st.subheader("Composition and Balance")
            st.write(critique.get("compositionAndBalance", empty_value))

            st.subheader("Use of Color")
            st.write(critique.get("useOfColor", empty_value))

            st.subheader("Brushwork and Texture")
            st.write(critique.get("brushworkAndTexture", empty_value))

            st.subheader("Originality and Creativity")
            st.write(critique.get("originalityAndCreativity", empty_value))

    # Composition Tab
    with tabs[2]:

        st.header("Composition")

        if "composition" not in response_obj:
            st.write("No critique data found")

        else:

            composition=response_obj["composition"]

            st.subheader("Color Palette")

            if "colorPalette" not in composition:
                st.write("Unknown")

            else:
                color_palette = composition["colorPalette"]

                # Convert to DataFrame with keys as Color column and values as Description
                df = pd.DataFrame.from_dict(color_palette, orient='index')

                # Rename columns
                df = df.rename(columns={0:'Description'})
                df.insert(0, 'Area', df.index)

                # Reorder columns
                df = df[['Area', 'Description']]
                del df[df.columns[0]]
                st_table = df.to_html(escape=False)
                st.markdown(st_table, unsafe_allow_html=True)

                st.markdown("\n")

            st.subheader("Hex Colors")

            if "hexColors" not in composition:
                st.write("Unknown")

            else:
                hex_colors = process_hex_colors(composition["hexColors"])
                df = pd.DataFrame(hex_colors, columns=["Area", "Colors"])

                st_table = df.to_html(escape=False)
                st.markdown(st_table, unsafe_allow_html=True)

    # Similar Artists Tab
    with tabs[3]:

        st.header("Similar Artists")

        if "similarArtists" not in response_obj:
            st.write("No similar artist data found")

        else:

            similar_artists=response_obj["similarArtists"]

            if len(similar_artists) >= 1:

                # Reformat rows to include Artist birth/death and wikipedia link
                for row in similar_artists:
                    name = f"{row['artistName']} ({row['artistBirthYear']}-{row['artistDeathYear']})"
                    #link = f'{row["artistWikipediaLink"]}'
                    link = f'<a href="{row["artistWikipediaLink"]} target="_blank">{row["artistWikipediaLink"]}</a>'
                    row["Artist"] = f"{name} {link}"
                    row["Explanation"] = row["explanation"]

                # Use upper-case syntax for Columns
                df = pd.DataFrame( similar_artists, columns=("Artist", "Explanation"))

                # Convert table to markdown format for easier rendering of HTML/href links
                st_table = df.to_html(escape=False)
                st.markdown(st_table, unsafe_allow_html=True)

            else:
                st.write("No similar artists found")

    # Similar Paintings Tab
    with tabs[4]:

        st.header("Similar Paintings")

        if "similarPaintings" not in response_obj:
            st.write("No similar painting data found")

        else:

            similar_paintings=response_obj["similarPaintings"]

            if len(similar_paintings) >= 1:

                # Reformat rows
                for row in similar_paintings:
                    # artistName = f"{row['artistName']} ({row['artistBirthYear']}-{row['artistDeathYear']})"
                    # link = f'<a href="{row["artistWikipediaLink"]} target="_blank">{row["artistWikipediaLink"]}</a>'
                    # row["Artist"] = f"{artistName}"

                    # Outputting full object for now, since this may be a complex object or string
                    if "artist" in row:

                        artist = row["artist"]

                        if isinstance(artist, str):
                            row["Artist"] = artist

                        if isinstance(artist, dict):
                            artistName = artist.get("artistName", "Unknown")
                            birth = artist.get("artistBirthYear", "?")
                            death = artist.get("artistDeathYear", "?")

                            row["Artist"] = f"{artistName} ({birth}-{death})"

                    else:
                        row["Artist"] = "Unknown"

                    paintingName = f"{row['painting']} ({row['yearOfPainting']})"
                    row["Painting"] = f"{paintingName}"

                    # Painting links are not reliable, so excluding for now
                    short_link = row["paintingLink"][:100]
                    link = f'<a href="{row["paintingLink"]} target="_blank">{short_link}</a>'
                    row["PaintingLink"] = f"{link}"
                    row["Year"] = row["yearOfPainting"]


                 # Use upper-case syntax for Columns
                df = pd.DataFrame( similar_paintings, columns=("Artist", "Painting", "Year"))
                st_table = df.to_html(escape=False)
                st.markdown(st_table, unsafe_allow_html=True)

            else:
                st.write("No similar paintings found")

    # Debug - JSON Output Tab
    if DEBUG:
        with tabs[5]:
            st.header("JSON Response")
            st.write(response_obj)


def display_image(image):

    image_fullsize = st.toggle('Fullsize Image')
    if image_fullsize:
        st.image(image, caption='Analyzed Image')
    else:
        st.image(image, caption='Analyzed Image', width=250)

def render_sidebar():

        with st.sidebar:
            st.markdown("---")
            st.markdown("# About")
            st.markdown("""
            Art Analyzer - Analyze artwork using GPT Vision and LLM - Version 
            """ +  version.__version__)
            st.markdown("""
            This tool is a work in progress. You can contribute to the project on GitHub (https://github.com/ericblue/art-analyzer) with your feedback and suggestions💡.

            **Author**: Eric Blue\n
            **Web**: https://eric-blue.com\n
            **Art**: https://ericblueart.com
            """)

            st.markdown("---")

            st.markdown(
                "## How to use\n"
                "1. Enter your [Gemini API key](https://makersuite.google.com/app/apikey) below 🔑\n"  # noqa: E501
                "2. Upload an image containing artwork 🖼️\n"
                "3. After processing, review the analysis in the tabs at the bottom of the page 🔍\n"
            )

            st.markdown("---")

# Main Streamlit App
def main():

    st.title("Art Analyzer")
    st.header("Analyze artwork using GPT Vision and LLM")
    st.write("""
    Art Analyzer is an app that uses GPT Vision (See: https://platform.openai.com/docs/guides/vision) to identify artwork from images and AI language models like GPT-4 
    to provide detailed critiques of paintings, drawings, and other visual art forms. Users can upload an image of a piece for review, and the app will generate an analysis 
    of the artwork covering composition, use of color, brushwork/texture, emotional impact, originality/creativity, and recommendations of similar artists and paintings.

    Can we really use AI as an art critic or expert?  Yes and No.  This app is a fun experiment to see how far along GPT Vision has come, and the results are generally very
    good and surprisingly detailed.  But, if you are looking to analyze and critique artwork in a more official capacity feel free to defer to art historians, experts, and enthusiasts.

    """)

    example_html = """
        For quick examples, see:
        * <a href="/?example=example4">Vincent van Gogh</a> 
        * <a href="/?example=example3">David Hockney</a> 
        * <a href="/?example=example2">John Atkinson Grimshaw</a> 
        * <a href="/?example=example1">Eric Blue [me]</a>
        * Or <a href="/">Upload your own image</a> to try it out.
    """
    st.markdown(example_html, unsafe_allow_html=True)

    render_sidebar()

    examples = {
        "example1": {
            "json_path": "examples/example1.json",
            "image_path": "examples/Eric_Blue-Clouds_At_Night.jpg"
        },
        "example2": {
            "json_path": "examples/example2.json",
            "image_path": "examples/John_Atkinson_Grimshaw_-_November_1879.jpeg"
        },
        "example3": {
            "json_path": "examples/example3.json",
            "image_path": "examples/David_Hockney_Garrowby_Hill.jpg"
        },
        "example4": {
            "json_path": "examples/example4.json",
            "image_path": "examples/Van_Gogh_-_Starry_Night.jpeg"
        }
    }



    query_params = st.experimental_get_query_params()
    #st.write(query_params)

    # Load example data for preview
    if 'example' in query_params:

        example = query_params["example"][0]

        if example not in examples:
            st.error("Example not found!")
            st.stop()


        image_path=examples[example]["image_path"]
        st.write("Loading example... " + image_path)
        image = Image.open(image_path)

        display_image(image)

        try:
            json_path = examples[example]["json_path"]
            response_json = load_response_json(json_path)
            response_obj = process_response_json(response_json)
            render_results(response_obj)
        except Exception as e:
            LOGGER.error("Top level error handling response", exc_info=True)
            error_msg = e.args[0]
            st.error("Error processing and rendering Example JSON results.  Reason = " +  error_msg)

    # Require OpenAI API key and file upload for processing
    else:

        api_key = get_gemini_api_key()

        if DEBUG:

            LOGGER.info("Enabling load local json toggle...")
            local_json_enabled = st.toggle("Load local JSON")

            global LOAD_LOCAL_JSON

            if local_json_enabled:
                LOGGER.info("Setting  LOAD_LOCAL_JSON = True")
                LOAD_LOCAL_JSON = True
            else:
                LOGGER.info("Setting  LOAD_LOCAL_JSON = False")
                LOAD_LOCAL_JSON = False

        uploaded_file = st.file_uploader("Choose an image...")

        if uploaded_file is not None:

            image = Image.open(uploaded_file)
            display_image(image)

            success=st.success("File Uploaded Successfully!")
            time.sleep(1)
            success.empty()

            try:
                response_obj = analyze_image(uploaded_file, api_key)
                render_results(response_obj)
            except Exception as e:
                LOGGER.error("Top level error handling response", exc_info=True)
                error_msg = e.args[0]
                st.error("Error processing and rendering JSON results. Reason = " +  error_msg)



if __name__ == '__main__':
    main()