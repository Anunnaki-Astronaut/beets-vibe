# Beets-Flask: Web Interface for Music Library Management

## Project Overview

Beets-Flask is a modern, opinionated web interface built around the popular Beets music organizer tool. It provides a user-friendly web-based solution for managing digital music collections with enhanced automation and preview capabilities.

## Main Objectives

- **Enhanced Music Import Workflow**: Streamline the process of importing music files with intelligent preview generation
- **Web-Based Management**: Provide a modern web interface for the traditionally command-line focused Beets tool
- **Automated Processing**: Enable auto-import of high-confidence music matches while allowing manual review for uncertain cases
- **Real-Time Monitoring**: Monitor multiple music folders (inboxes) for new files and process them automatically

## Key Features

### Core Functionality
- **Auto-Generated Previews**: Preview what Beets would do before importing, showing metadata matches
- **Smart Auto-Import**: Automatically import tracks with high confidence matches
- **Manual Import Control**: GUI-based import with candidate selection for uncertain matches
- **Undo Capability**: Reverse imports when needed
- **Multi-Inbox Support**: Monitor and manage multiple source folders simultaneously

### User Interface
- **Web Terminal**: Built-in terminal interface for advanced users
- **Library Browser**: Search and browse the complete music collection
- **Real-Time Status**: Live updates during import and processing operations
- **Audio Player**: Integrated player with waveform visualization
- **Responsive Design**: Modern React-based interface

### Technical Features
- **Docker Integration**: Full containerization with Docker Compose support
- **WebSocket Communication**: Real-time updates and status monitoring
- **Database Management**: SQLite/MySQL support for metadata storage
- **File Monitoring**: Automatic detection of new music files using Watchdog
- **Job Queue System**: Redis-backed task queue for background processing

## Technology Stack

### Backend (Python 3.11+)
- **Web Framework**: Quart (ASGI implementation of Flask)
- **Music Processing**: Beets 2.5.1 for metadata extraction and organization
- **Database**: SQLAlchemy ORM with SQLite/MySQL support
- **Job Queue**: Redis + RQ for asynchronous task processing
- **WebSocket**: Python-SocketIO for real-time communication
- **File Monitoring**: Watchdog for automatic folder monitoring
- **Image Processing**: Pillow for cover art handling
- **Audio Analysis**: NumPy, Pandas for audio metadata processing

### Frontend (React/TypeScript)
- **Framework**: React 19.2.0 with TypeScript
- **State Management**: TanStack React Query for server state
- **Routing**: TanStack React Router for navigation
- **UI Components**: Material-UI (MUI) for consistent design
- **Build Tool**: Vite for fast development and optimized builds
- **Real-Time**: Socket.IO client for WebSocket communication
- **Audio Visualization**: WaveSurfer.js for waveform display
- **Drag & Drop**: DnD Kit for interactive user interfaces

### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Development**: Docker Compose for local development
- **Testing**: pytest with comprehensive test coverage
- **Code Quality**: Ruff linter, MyPy type checking
- **Documentation**: Sphinx-based documentation system

## Significance

Beets-Flask addresses the gap between Beets' powerful command-line capabilities and the need for a more accessible, visual interface. It democratizes access to advanced music library management features while preserving the power and flexibility that Beets users expect.

The project is particularly valuable for:
- **Music Enthusiasts**: Who want sophisticated metadata management without command-line complexity
- **Large Collections**: Managing extensive music libraries with automated organization
- **Batch Processing**: Efficient handling of large music imports with preview-based workflows
- **Cross-Platform Users**: Web-based interface accessible from any device
- **Workflow Automation**: Real-time monitoring and processing of music files

## Current Status

The project is in active development with version 1.2.0-rc4, featuring a stable Docker-based deployment model and comprehensive documentation. It maintains backward compatibility with Beets while adding modern web interface capabilities.