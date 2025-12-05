# Metadata Source & Credentials Settings UI

## Overview

The Metadata Settings UI provides a web-based interface for configuring Beets metadata plugins and their associated credentials. This feature allows users to enable/disable plugins and manage their configuration settings through an intuitive web interface, replacing the need to directly edit YAML configuration files.

## Purpose

- **User Experience**: Provide a user-friendly interface for managing metadata plugin configurations
- **Security**: Safely handle sensitive credentials by redacting them in the UI while allowing updates
- **Configuration Management**: Enable real-time plugin configuration changes without manual file editing
- **Plugin Support**: Support commonly used metadata plugins with their specific configuration needs

## Feature Requirements

### Core Functionality

1. **Plugin Management Interface**
   - Display all supported metadata plugins with their current status
   - Allow users to enable/disable individual plugins
   - Show plugin-specific configuration settings
   - Provide clear indication of which plugins are currently active

2. **Credential Management**
   - Display configuration fields for each plugin
   - Redact sensitive fields (tokens, secrets, API keys) for security
   - Allow users to update credentials through secure form inputs
   - Preserve existing non-sensitive settings

3. **Real-time Configuration**
   - Apply configuration changes immediately without restart
   - Provide feedback on successful updates
   - Handle validation errors gracefully
   - Create automatic backups before changes

### In-Scope Plugins

The following metadata plugins are fully supported by the backend implementation:

1. **discogs** - Discogs music database integration
2. **spotify** - Spotify metadata and audio features
3. **musicbrainz** - MusicBrainz database and acoustic analysis
4. **beatport** - Beatport electronic music database
5. **lyrics** - Lyrics fetching and display
6. **autobpm** - Automatic BPM detection
7. **keyfinder** - Musical key detection
8. **replaygain** - ReplayGain audio loudness analysis

## Backend Implementation

### API Endpoints

#### GET `/api_v1/config/metadata_plugins`
**Purpose**: Retrieve current metadata plugin configurations

**Response Format**:
```json
{
  "discogs": {
    "enabled": true,
    "settings": {
      "token": "********",
      "secret": "********",
      "user_agent": "Custom User Agent"
    }
  },
  "spotify": {
    "enabled": false,
    "settings": {
      "api_key": "********"
    }
  },
  "musicbrainz": {
    "enabled": true,
    "settings": {}
  },
  "beatport": {
    "enabled": false,
    "settings": {}
  },
  "lyrics": {
    "enabled": false,
    "settings": {}
  },
  "autobpm": {
    "enabled": false,
    "settings": {
      "max_tempo": "200"
    }
  },
  "keyfinder": {
    "enabled": false,
    "settings": {}
  },
  "replaygain": {
    "enabled": false,
    "settings": {}
  }
}
```

#### POST `/api_v1/config/metadata_plugins`
**Purpose**: Update metadata plugin configuration

**Request Format**:
```json
{
  "plugin": "discogs",
  "enabled": true,
  "settings": {
    "token": "new_token_value",
    "secret": "new_secret_value",
    "user_agent": "Custom User Agent"
  }
}
```

**Success Response**:
```json
{
  "status": "ok"
}
```

**Error Responses**:
- `400 Bad Request`: Missing plugin name or invalid enabled type
- `500 Internal Server Error`: Configuration update failed

### Configuration Service

The `ConfigService` class handles all metadata plugin configuration operations:

#### Key Features
- **Plugin Validation**: Ensures only supported plugins can be configured
- **Security**: Automatic redaction of sensitive fields (fields containing "token", "secret", or "key")
- **Backup Management**: Automatic backup creation before any configuration changes
- **YAML Preservation**: Uses `ruamel.yaml` to maintain YAML structure and comments

#### Supported Operations
- `get_metadata_plugins_config()`: Fetch current plugin configurations
- `update_metadata_plugin_config(plugin_name, settings, enabled)`: Update plugin settings

### YAML Handling

The backend uses **`ruamel.yaml`** library for YAML file operations, which provides:
- **Comment Preservation**: Maintains existing comments in configuration files
- **Structure Preservation**: Preserves YAML formatting and structure
- **Safe Updates**: Atomic write operations with automatic backup creation

This ensures that manual configuration changes and comments are preserved when the UI updates plugin settings.

## Security Considerations

### Sensitive Data Handling
- **Display Security**: Sensitive fields are redacted in API responses (shown as `********`)
- **Input Validation**: Server-side validation prevents injection attacks
- **Automatic Backups**: Configuration changes are automatically backed up before application
- **Error Handling**: Generic error messages prevent information disclosure

### Field Redaction Rules
The following field patterns are automatically redacted in responses:
- Fields containing "token" (e.g., `access_token`, `client_token`)
- Fields containing "secret" (e.g., `client_secret`, `api_secret`)
- Fields containing "key" (e.g., `api_key`, `secret_key`)

**Note**: These fields are still accepted as input for updates but are displayed as redacted in responses.

## User Interface Requirements

### Layout and Design
- **Plugin Grid**: Display plugins in a responsive grid layout
- **Status Indicators**: Clear visual indicators for enabled/disabled status
- **Settings Forms**: Expandable sections for each plugin's configuration
- **Action Buttons**: Enable/disable toggles and save/update buttons

### User Experience
- **Immediate Feedback**: Show success/error states after configuration changes
- **Form Validation**: Client-side validation for required fields and data types
- **Progressive Disclosure**: Expandable plugin settings to reduce interface clutter
- **Mobile Responsive**: Ensure usability on mobile devices and tablets

### Error Handling
- **Validation Errors**: Clear error messages for invalid inputs
- **Network Errors**: Graceful handling of connection issues
- **Server Errors**: User-friendly error messages with retry options
- **Partial Updates**: Handle cases where some plugins update successfully while others fail

## Technical Implementation Details

### State Management
- **Plugin State**: Track enabled/disabled status for each plugin
- **Settings State**: Manage plugin-specific configuration values
- **Loading States**: Show loading indicators during API calls
- **Dirty State**: Track unsaved changes to prevent data loss

### API Integration
- **Fetch Configuration**: Load current plugin settings on component mount
- **Update Configuration**: Send changes to backend with proper error handling
- **Optimistic Updates**: Update UI immediately while waiting for server response
- **Rollback Capability**: Revert changes if server update fails

### Form Handling
- **Dynamic Forms**: Generate forms based on plugin-specific configuration schemas
- **Type Safety**: Ensure proper data types for different configuration fields
- **Conditional Fields**: Show/hide fields based on plugin selection or other values
- **Default Values**: Provide sensible defaults for plugin configuration options

## Testing Considerations

### Backend Testing
- **Unit Tests**: Comprehensive test coverage for ConfigService methods
- **Integration Tests**: API endpoint testing with various plugin configurations
- **Security Tests**: Verify sensitive field redaction and input validation
- **Backup Tests**: Ensure backup creation and restoration functionality

### Frontend Testing
- **Component Tests**: Test individual UI components and their interactions
- **Integration Tests**: End-to-end testing of configuration workflows
- **Error Handling Tests**: Verify proper error states and user feedback
- **Responsive Tests**: Ensure functionality across different screen sizes

## Success Criteria

### Functional Requirements
- [ ] All 8 supported plugins can be enabled/disabled through the UI
- [ ] Plugin-specific settings can be viewed and modified
- [ ] Sensitive fields are properly redacted in the display
- [ ] Configuration changes are immediately applied
- [ ] Automatic backups are created before any changes

### User Experience Requirements
- [ ] Interface is intuitive and requires no training
- [ ] All operations complete within 3 seconds
- [ ] Error states are clearly communicated
- [ ] Interface is fully responsive across device sizes
- [ ] Loading states provide appropriate feedback

### Security Requirements
- [ ] No sensitive data is exposed in client-side storage
- [ ] All API endpoints require proper authentication
- [ ] Input validation prevents injection attacks
- [ ] Configuration changes are auditable through backup files

## Dependencies

### Backend Dependencies
- `ruamel.yaml`: YAML file handling with comment preservation
- `beets_flask.config`: Configuration management system
- `quart`: Web framework for API endpoints

### Frontend Dependencies
- React components for user interface
- Form handling libraries for plugin configuration
- HTTP client for API communication
- State management for plugin configurations

## Implementation Notes

### Plugin Configuration Patterns
Each plugin may have different configuration requirements:
- **Authentication**: Some plugins require API keys or OAuth tokens
- **Behavioral Settings**: Options for how plugins interact with metadata sources
- **Performance Tuning**: Settings for timeout values, retry attempts, etc.
- **User Preferences**: Display options and formatting preferences

### Future Extensibility
The plugin system is designed to be easily extensible:
- New plugins can be added to `SUPPORTED_METADATA_PLUGINS` list
- Configuration schemas can be defined dynamically
- Plugin-specific UI components can be registered
- Backend service methods can be extended for new plugin types

## Deployment Considerations

### Configuration Migration
- **Existing Configs**: Ensure compatibility with existing Beets configuration files
- **Backup Migration**: Provide tools for migrating from manual to UI-based configuration
- **Rollback Strategy**: Enable easy rollback to previous configurations if needed

### Performance Impact
- **Startup Time**: Plugin configuration loading should not significantly impact startup
- **Memory Usage**: Efficient storage and caching of plugin configurations
- **API Response Times**: Ensure plugin configuration endpoints respond quickly

This specification provides the foundation for implementing a comprehensive metadata settings UI that enhances the user experience while maintaining security and compatibility with the existing Beets ecosystem.