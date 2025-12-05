import { useState } from "react";
import {
    Accordion,
    AccordionDetails,
    AccordionSummary,
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    Collapse,
    FormControlLabel,
    Grid,
    Switch,
    TextField,
    Typography,
    useTheme,
} from "@mui/material";
import { ExpandMore } from "@mui/icons-material";
import { createFileRoute } from "@tanstack/react-router";

import { PageWrapper } from "@/components/common/page";
import {
    useMetadataPlugins,
    updateMetadataPluginMutation,
    MetadataPluginsConfig,
} from "@/api/config";

export const Route = createFileRoute("/settings/metadata")({
    component: MetadataSettingsPage,
});

function MetadataSettingsPage() {
    const theme = useTheme();
    const plugins = useMetadataPlugins();
    const updateMutation = updateMetadataPluginMutation();
    const [alertMessage, setAlertMessage] = useState<{
        message: string;
        severity: "success" | "error";
    } | null>(null);

    const handleSavePlugin = async (
        pluginName: keyof MetadataPluginsConfig,
        enabled: boolean,
        settings: Record<string, string>
    ) => {
        try {
            await updateMutation.mutateAsync({
                plugin: pluginName,
                enabled,
                settings,
            });
            setAlertMessage({
                message: `Successfully updated ${pluginName} settings`,
                severity: "success",
            });
        } catch (error) {
            setAlertMessage({
                message: `Failed to update ${pluginName} settings`,
                severity: "error",
            });
        }
    };

    return (
        <PageWrapper
            sx={{
                display: "flex",
                flexDirection: "column",
                gap: theme.spacing(2),
                padding: theme.spacing(2),
            }}
        >
            <Typography variant="h4" component="h1" gutterBottom>
                Metadata Sources Settings
            </Typography>
            <Typography variant="body1" color="text.secondary" gutterBottom>
                Configure metadata plugins for music library management. Enable/disable plugins and manage their authentication settings.
            </Typography>

            <Collapse in={!!alertMessage}>
                {alertMessage && (
                    <Alert
                        severity={alertMessage.severity}
                        onClose={() => setAlertMessage(null)}
                        sx={{ mb: 2 }}
                    >
                        {alertMessage.message}
                    </Alert>
                )}
            </Collapse>

            <Box sx={{ width: "100%", mb: 3 }}>
                <Grid container spacing={2}>
                    {Object.entries(plugins).map(([pluginName, config]) => (
                        <Grid item xs={12} md={6} key={pluginName}>
                            <PluginSettingsCard
                                pluginName={pluginName as keyof MetadataPluginsConfig}
                                config={config}
                                onSave={handleSavePlugin}
                                isUpdating={updateMutation.isPending}
                            />
                        </Grid>
                    ))}
                </Grid>
            </Box>
        </PageWrapper>
    );
}

interface PluginSettingsCardProps {
    pluginName: keyof MetadataPluginsConfig;
    config: MetadataPluginsConfig[keyof MetadataPluginsConfig];
    onSave: (
        pluginName: keyof MetadataPluginsConfig,
        enabled: boolean,
        settings: Record<string, string>
    ) => Promise<void>;
    isUpdating: boolean;
}

function PluginSettingsCard({
    pluginName,
    config,
    onSave,
    isUpdating,
}: PluginSettingsCardProps) {
    const [enabled, setEnabled] = useState(config.enabled);
    const [settings, setSettings] = useState<Record<string, string>>(config.settings);
    const [expanded, setExpanded] = useState(false);

    const hasSettings = Object.keys(config.settings).length > 0;
    const hasChanges =
        enabled !== config.enabled ||
        JSON.stringify(settings) !== JSON.stringify(config.settings);

    const handleSave = () => {
        onSave(pluginName, enabled, settings);
    };

    const handleCancel = () => {
        setEnabled(config.enabled);
        setSettings({ ...config.settings });
    };

    const getFieldType = (fieldName: string): "text" | "password" => {
        const sensitiveFields = ["token", "secret", "key"];
        return sensitiveFields.some(sensitive => fieldName.toLowerCase().includes(sensitive))
            ? "password"
            : "text";
    };

    const getFieldLabel = (fieldName: string): string => {
        return fieldName
            .replace(/_/g, " ")
            .replace(/\b\w/g, l => l.toUpperCase());
    };

    return (
        <Card>
            <CardContent>
                <Box
                    sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        mb: hasSettings ? 0 : 2,
                    }}
                >
                    <Typography variant="h6" component="h2">
                        {pluginName.charAt(0).toUpperCase() + pluginName.slice(1)}
                    </Typography>
                    <FormControlLabel
                        control={
                            <Switch
                                checked={enabled}
                                onChange={(e) => setEnabled(e.target.checked)}
                                color="primary"
                            />
                        }
                        label={enabled ? "Enabled" : "Disabled"}
                    />
                </Box>

                {hasSettings && (
                    <Accordion
                        expanded={expanded}
                        onChange={(_, isExpanded) => setExpanded(isExpanded)}
                    >
                        <AccordionSummary expandIcon={<ExpandMore />}>
                            <Typography variant="subtitle1">
                                Settings ({Object.keys(settings).length} fields)
                            </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                                {Object.entries(settings).map(([fieldName, value]) => (
                                    <TextField
                                        key={fieldName}
                                        label={getFieldLabel(fieldName)}
                                        type={getFieldType(fieldName)}
                                        value={value}
                                        onChange={(e) =>
                                            setSettings(prev => ({
                                                ...prev,
                                                [fieldName]: e.target.value,
                                            }))
                                        }
                                        fullWidth
                                        variant="outlined"
                                        size="small"
                                        placeholder={
                                            value === "********" ? "Enter new value" : ""
                                        }
                                    />
                                ))}
                            </Box>
                        </AccordionDetails>
                    </Accordion>
                )}

                {hasChanges && (
                    <Box
                        sx={{
                            display: "flex",
                            gap: 1,
                            mt: 2,
                            justifyContent: "flex-end",
                        }}
                    >
                        <Button
                            variant="outlined"
                            size="small"
                            onClick={handleCancel}
                            disabled={isUpdating}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="contained"
                            size="small"
                            onClick={handleSave}
                            disabled={isUpdating}
                        >
                            {isUpdating ? "Saving..." : "Save"}
                        </Button>
                    </Box>
                )}
            </CardContent>
        </Card>
    );
}