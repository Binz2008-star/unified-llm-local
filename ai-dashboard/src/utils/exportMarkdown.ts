import { Conversation, SecondBrainProject, SystemTelemetry } from '../types';

/**
 * Formats a programming session into comprehensive GitHub Flavored Markdown (GFM).
 * Designed for team documentation, PR notes, architecture reviews, and issue trackers.
 */
export function formatConversationToGFM(
  conversation: Conversation,
  project?: SecondBrainProject,
  telemetry?: SystemTelemetry | null
): string {
  const dateStr = new Date(conversation.createdAt).toLocaleString('en-US', {
    dateStyle: 'full',
    timeStyle: 'medium',
  });

  const projName = project?.name || conversation.projectId || 'Second Brain Project';
  const projPath = project?.path || 'N/A';
  const projTech = project?.tech || 'Full-Stack • AI Agents';

  let md = '';

  // Title & Badges
  md += `# 🚀 Code It Engineering Session: ${conversation.title || 'Architecture & Code Synthesis'}\n\n`;
  md += `> **Automated Session Documentation** — Formatted in GitHub Flavored Markdown (GFM) for team sharing, knowledge base syncing, and repository logging.\n\n`;

  // Metadata Table (GFM compliant)
  md += `## 📋 Session Overview\n\n`;
  md += `| Attribute | Specification |\n`;
  md += `| :--- | :--- |\n`;
  md += `| **Session Title** | \`${conversation.title}\` |\n`;
  md += `| **Target Project** | **${projName}** |\n`;
  md += `| **Local Host Path** | \`${projPath}\` |\n`;
  md += `| **Tech Stack** | \`${projTech}\` |\n`;
  md += `| **Date & Time** | ${dateStr} |\n`;
  md += `| **Total Exchanges** | ${Math.ceil(conversation.messages.length / 2)} interactions (${conversation.messages.length} messages) |\n`;
  if (telemetry) {
    md += `| **Execution Host** | ROBEN (Windows_NT, ${telemetry.cpu_cores?.length || 12} Cores, CPU: ${telemetry.cpu}%, Disk: ${telemetry.disk.usePct}%) |\n`;
    md += `| **Memory Store** | Neon Vector Database (768-dim Nomics) • Second Brain v4 |\n`;
  }
  md += `\n---\n\n`;

  // Table of Contents
  const userMessages = conversation.messages.filter((m) => m.role === 'user');
  if (userMessages.length > 0) {
    md += `## 📑 Table of Contents\n\n`;
    userMessages.forEach((msg, idx) => {
      const anchorTitle = (msg.content.slice(0, 45).trim() || `Interaction ${idx + 1}`)
        .toLowerCase()
        .replace(/[^a-z0-9\u0600-\u06FF]+/g, '-')
        .replace(/(^-|-$)/g, '');
      const displayTitle = msg.content.slice(0, 60).replace(/\n/g, ' ') || `Interaction #${idx + 1}`;
      md += `- [Interaction #${idx + 1}: ${displayTitle}](#interaction-${idx + 1}-${anchorTitle})\n`;
    });
    md += `- [📦 Code Artifacts & Attached Files](#-code-artifacts--attached-files)\n`;
    md += `\n---\n\n`;
  }

  // Session Transcript
  md += `## 💬 Interactive Engineering Dialogue\n\n`;

  let interactionCount = 0;
  for (let i = 0; i < conversation.messages.length; i++) {
    const msg = conversation.messages[i];

    if (msg.role === 'user') {
      interactionCount++;
      const anchorTitle = (msg.content.slice(0, 45).trim() || `Interaction ${interactionCount}`)
        .toLowerCase()
        .replace(/[^a-z0-9\u0600-\u06FF]+/g, '-')
        .replace(/(^-|-$)/g, '');

      md += `### <a id="interaction-${interactionCount}-${anchorTitle}"></a>Interaction #${interactionCount}\n\n`;
      md += `#### 👤 User Prompt\n\n`;
      md += `> ${msg.content.split('\n').join('\n> ')}\n\n`;

      if (msg.attachedFiles && msg.attachedFiles.length > 0) {
        md += `##### 📎 Attached Workspace Files (${msg.attachedFiles.length})\n\n`;
        md += `| File Name | Size | Preview / Summary |\n`;
        md += `| :--- | :--- | :--- |\n`;
        msg.attachedFiles.forEach((file) => {
          const sizeKb = Math.round(file.size / 1024);
          const snippet = file.content ? `\`${file.content.slice(0, 60).replace(/\n/g, ' ')}...\`` : '_Binary / Empty_';
          md += `| \`${file.name}\` | ${sizeKb} KB | ${snippet} |\n`;
        });
        md += `\n`;

        // If files have content, append collapsible details
        msg.attachedFiles.forEach((file) => {
          if (file.content) {
            const ext = file.name.split('.').pop() || '';
            md += `<details>\n<summary>📄 View Full Content: <code>${file.name}</code></summary>\n\n`;
            md += `\`\`\`${ext}\n${file.content}\n\`\`\`\n\n</details>\n\n`;
          }
        });
      }
    } else {
      // Assistant response
      md += `#### 🤖 Second Brain AI Response\n\n`;

      if (msg.modelSource) {
        md += `*Generated via \`${msg.modelSource}\` engine*\n\n`;
      }

      // Multi-Agent Pipeline execution status
      if (msg.agentPhases && msg.agentPhases.length > 0) {
        md += `##### 🔄 Multi-Agent Pipeline Status\n\n`;
        md += `| Phase | Agent Role | Status | Execution Detail |\n`;
        md += `| :--- | :--- | :--- | :--- |\n`;
        msg.agentPhases.forEach((p, pIdx) => {
          const icon = p.status === 'completed' ? '✅' : p.status === 'active' ? '⏳' : '⚪';
          md += `| 0${pIdx + 1} | **${p.label}** | ${icon} \`${p.status}\` | ${p.detail || 'Executed standard verification'} |\n`;
        });
        md += `\n`;
      }

      // Thinking steps
      if (msg.thinkingSteps && msg.thinkingSteps.length > 0) {
        md += `<details open>\n<summary>🧠 <b>Architectural Reasoning Process</b> (${msg.thinkingSteps.length} steps)</summary>\n\n`;
        msg.thinkingSteps.forEach((step, sIdx) => {
          md += `${sIdx + 1}. ${step}\n`;
        });
        md += `\n</details>\n\n`;
      }

      // Content explanation
      if (msg.content) {
        md += `##### 💡 Architecture & Solution Explanation\n\n`;
        md += `${msg.content}\n\n`;
      }

      // Code Artifact
      if (msg.artifact) {
        const art = msg.artifact;
        md += `##### 🛠️ Generated Code Artifact: \`${art.title}\`\n\n`;
        if (art.description) {
          md += `*${art.description}*\n\n`;
        }
        md += `\`\`\`${art.language || 'typescript'}\n`;
        md += `${art.code}\n`;
        md += `\`\`\`\n\n`;
      }

      md += `---\n\n`;
    }
  }

  // Consolidated Code Artifacts & Attached Files Manifest
  md += `## 📦 Code Artifacts & Attached Files\n\n`;
  const artifacts = conversation.messages
    .filter((m) => m.artifact)
    .map((m) => m.artifact!);

  if (artifacts.length > 0) {
    md += `### Generated Files (${artifacts.length})\n\n`;
    md += `| File | Language | Target Project | Description |\n`;
    md += `| :--- | :--- | :--- | :--- |\n`;
    artifacts.forEach((art) => {
      md += `| **\`${art.title}\`** | \`${art.language}\` | \`${art.projectId || projName}\` | ${art.description || 'System module'} |\n`;
    });
    md += `\n`;
  } else {
    md += `_No isolated code files generated in this session (dialogue was conceptual/analytical)._\n\n`;
  }

  // Footer
  md += `\n---\n`;
  md += `*Exported from **Code It - Second Brain v4 Console** • Host: ROBEN • Local Project: \`${projName}\`*\n`;

  return md;
}

/**
 * Downloads a string as a file in the browser.
 */
export function downloadFile(content: string, filename: string, mimeType: string = 'text/markdown;charset=utf-8') {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
