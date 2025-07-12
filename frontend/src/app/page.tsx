"use client";

import { useState, useEffect } from "react";
import {
  Container,
  Title,
  TextInput,
  Button,
  Stack,
  Text,
  Alert,
  Paper,
  Group,
  Center,
  Box,
  ActionIcon,
  CopyButton,
  Tooltip,
} from "@mantine/core";
import {
  IconDownload,
  IconCheck,
  IconCopy,
  IconAlertCircle,
  IconLoaderQuarter,
} from "@tabler/icons-react";

export default function Home() {
  const [leagueId, setLeagueId] = useState("");
  const [autoGenerate, setAutoGenerate] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Function to get URL parameters
  const getUrlParams = () => {
    if (typeof window === "undefined") return {};

    const urlParams = new URLSearchParams(window.location.search);
    return {
      leagueId: urlParams.get("leagueId") || "",
      auto: urlParams.get("auto") === "true",
    };
  };

  // Function to update URL without page reload
  const updateUrl = (leagueId: string) => {
    if (typeof window === "undefined") return;

    const url = new URL(window.location.href);
    if (leagueId) {
      url.searchParams.set("leagueId", leagueId);
    } else {
      url.searchParams.delete("leagueId");
    }

    window.history.replaceState({}, "", url.toString());
  };

  // Initialize form with URL parameters
  useEffect(() => {
    const params = getUrlParams();
    if (params.leagueId) {
      setLeagueId(params.leagueId);
    }
    if (params.auto && params.leagueId) {
      setAutoGenerate(true);
    }
  }, []);

  // Auto-generate report if URL parameters indicate to do so
  useEffect(() => {
    if (autoGenerate && leagueId && !loading) {
      setAutoGenerate(false); // Prevent infinite loop
      handleSubmit(null);
    }
  }, [autoGenerate, leagueId, loading]);

  const handleSubmit = async (e?: React.FormEvent | null) => {
    if (e) {
      e.preventDefault();
    }

    if (!leagueId) {
      setError("Please fill in the league ID");
      return;
    }

    setError("");
    setSuccess("");
    setLoading(true);

    try {
      // Determine the API base URL - adjust this based on your deployment
      const apiBaseUrl =
        process.env.NODE_ENV === "production"
          ? "/api" // Same origin when served by Python API
          : "http://localhost:8000/api";

      const response = await fetch(`${apiBaseUrl}/report/${leagueId}`, {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`${errorData.detail || "Something went wrong"}`);
      }

      // Get the filename from the Content-Disposition header
      const contentDisposition = response.headers.get("Content-Disposition");
      const filename =
        contentDisposition?.match(/filename="(.+)"/)?.[1] || `fpl-motw-${leagueId}.csv`;

      // Create a blob from the response
      const blob = await response.blob();

      // Create a download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setSuccess("Report generated and downloaded successfully!");
    } catch (err: any) {
      console.error("Error generating report:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const autoGenerateUrl =
    typeof window !== "undefined" && leagueId
      ? `${window.location.origin}${window.location.pathname}?leagueId=${leagueId}&auto=true`
      : "";

  return (
    <Box
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #1a1b23 0%, #2d2f3a 100%)",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        padding: "4rem 1rem 2rem",
      }}
    >
      <Container size="sm" px="md">
        <Center>
          <Stack align="center" gap="xl" style={{ width: "100%", maxWidth: 400 }}>
            {/* Header */}
            <Title
              order={1}
              ta="center"
              c="green"
              style={{
                fontSize: "2.5rem",
                fontWeight: 700,
              }}
            >
              FPL Manager of the Week
            </Title>

            <Text
              size="lg"
              ta="center"
              c="dimmed"
              style={{
                marginTop: "-1rem",
                maxWidth: "350px",
              }}
            >
              Generate Manager of the Week report for your FPL mini-league
            </Text>

            {/* Main Form */}
            <Paper
              p="xl"
              radius="lg"
              style={{
                width: "100%",
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid rgba(64, 192, 87, 0.2)",
                backdropFilter: "blur(10px)",
              }}
            >
              <form onSubmit={handleSubmit}>
                <Stack gap="lg">
                  <TextInput
                    label="League ID"
                    placeholder="Enter your FPL league ID"
                    value={leagueId}
                    onChange={(e) => {
                      setLeagueId(e.target.value);
                      updateUrl(e.target.value);
                    }}
                    disabled={loading}
                    styles={{
                      label: { color: "white", fontWeight: 500 },
                    }}
                  />

                  <Button
                    type="submit"
                    disabled={!leagueId || loading}
                    leftSection={<IconDownload size={18} />}
                    size="lg"
                    radius="md"
                    style={{
                      marginTop: "1rem",
                      backgroundColor:
                        !leagueId || loading
                          ? "var(--mantine-color-gray-6)"
                          : "var(--mantine-color-green-6)",
                      color:
                        !leagueId || loading ? "var(--mantine-color-gray-4)" : "white",
                      cursor: !leagueId || loading ? "not-allowed" : "pointer",
                      opacity: !leagueId || loading ? 0.6 : 1,
                    }}
                  >
                    Generate
                  </Button>
                </Stack>
              </form>
            </Paper>

            {/* Status Messages */}
            {loading && (
              <Alert
                icon={
                  <div
                    style={{
                      animation: "spin 1s linear infinite",
                      display: "inline-block",
                      transformOrigin: "center",
                    }}
                  >
                    <IconLoaderQuarter size={18} />
                  </div>
                }
                color="blue"
                variant="filled"
                style={{
                  width: "100%",
                }}
              >
                <style
                  dangerouslySetInnerHTML={{
                    __html: `
                    @keyframes spin {
                      from { transform: rotate(0deg); }
                      to { transform: rotate(360deg); }
                    }
                  `,
                  }}
                />
                Generating Manager of the Week report...
              </Alert>
            )}

            {error && (
              <Alert
                icon={<IconAlertCircle size={18} />}
                color="red"
                variant="filled"
                style={{ width: "100%" }}
              >
                {error}
              </Alert>
            )}

            {success && (
              <Alert
                icon={<IconCheck size={18} />}
                color="green"
                variant="filled"
                style={{ width: "100%" }}
              >
                {success}
              </Alert>
            )}

            {/* Shareable URL Section */}
            {leagueId && (
              <Paper
                p="md"
                radius="md"
                style={{
                  width: "100%",
                  background: "rgba(64, 192, 87, 0.1)",
                  border: "1px solid rgba(64, 192, 87, 0.3)",
                }}
              >
                <Stack gap="sm">
                  <Text fw={500} c="green">
                    📋 Shareable URL
                  </Text>
                  <Text size="sm" c="dimmed">
                    Copy this URL to bookmark it or share with others:
                  </Text>

                  <Paper
                    p="xs"
                    radius="sm"
                    style={{
                      background: "rgba(255, 255, 255, 0.05)",
                      fontFamily: "monospace",
                      fontSize: "12px",
                      wordBreak: "break-all",
                    }}
                  >
                    <Text size="xs" c="white">
                      {autoGenerateUrl}
                    </Text>
                  </Paper>

                  <Group justify="center">
                    <CopyButton value={autoGenerateUrl}>
                      {({ copied, copy }) => (
                        <Tooltip label={copied ? "Copied" : "Copy auto-generate URL"}>
                          <ActionIcon
                            color={copied ? "teal" : "green"}
                            variant="light"
                            onClick={copy}
                          >
                            {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                          </ActionIcon>
                        </Tooltip>
                      )}
                    </CopyButton>
                  </Group>
                </Stack>
              </Paper>
            )}

            {/* Help Section */}
            <Paper
              p="md"
              radius="md"
              style={{
                width: "100%",
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
              }}
            >
              <Stack gap="xs">
                <Text fw={500} c="white">
                  🔍 How to find your League ID:
                </Text>
                <Text
                  size="sm"
                  c="dimmed"
                  component="ol"
                  style={{ paddingLeft: "1rem" }}
                >
                  <li>Navigate to your FPL mini-league</li>
                  <li>
                    Look at the URL - the league ID is the number after "/leagues/"
                  </li>
                  <li>
                    Example: if URL contains "/leagues/123456/", your league ID is
                    "123456"
                  </li>
                </Text>
              </Stack>
            </Paper>
          </Stack>
        </Center>
      </Container>
    </Box>
  );
}
