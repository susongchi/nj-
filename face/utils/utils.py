from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, session, request, send_from_directory, jsonify
from flask_restful import Resource, Api
from ultralytics import YOLO
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, logout_user, login_required, current_user, LoginManager
from datetime import datetime, timedelta
from flask_cors import CORS
from email.mime.text import MIMEText
import pymysql
import cv2
import base64
import numpy as np
import face_recognition
import os
import secrets
import smtplib