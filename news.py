import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from st_clickable_images import clickable_images
from newspaper import Article
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from streamlit_autorefresh import st_autorefresh
import time
import streamlit.components.v1 as components
import random