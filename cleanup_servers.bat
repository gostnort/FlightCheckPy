@echo off 
taskkill /F /FI "WINDOWTITLE eq memdb_port_server.py*" /T 
taskkill /F /FI "WINDOWTITLE eq streamlit*" /T 
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq memdb_port_server.py*" 
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq streamlit*" 
