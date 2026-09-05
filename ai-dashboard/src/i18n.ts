export type Language = 'ar' | 'en';

export interface Translations {
  appName: string;
  appSubtitle: string;
  projectSwitcher: string;
  active: string;
  connectedProjects: string;
  hostTelemetry: string;
  hostStatus: string;
  connected: string;
  newChat: string;
  clearChat: string;
  clearChatConfirm: string;
  exportChat: string;
  chatHistory: string;
  noHistory: string;
  modes: {
    title: string;
    fast: { label: string; desc: string };
    advanced: { label: string; desc: string };
    security: { label: string; desc: string };
  };
  input: {
    placeholder: string;
    attach: string;
    send: string;
    generating: string;
    attachments: string;
    removeFile: string;
  };
  welcome: {
    title: string;
    subtitle: string;
    prompts: Array<{ title: string; prompt: string }>;
  };
  message: {
    agentPipeline: string;
    completedPhases: string;
    phases: {
      researcher: string;
      architect: string;
      editor: string;
      tester: string;
      memory: string;
    };
    thinkingCompleted: string;
    thinkingActive: string;
    generatingResponse: string;
    copy: string;
    copied: string;
    interactiveFile: string;
    inspectCode: string;
    projectBadge: string;
  };
  drawer: {
    title: string;
    codeTab: string;
    outputTab: string;
    saveToProject: string;
    saving: string;
    saved: string;
    runTest: string;
    testing: string;
    copy: string;
    copied: string;
    download: string;
    lines: string;
    bytes: string;
    targetProject: string;
    outputPlaceholder: string;
  };
  telemetry: {
    title: string;
    hostSpecs: string;
    cpu: string;
    cpuHot: string;
    ram: string;
    ramOf: string;
    disk: string;
    diskFree: string;
    coresLoad: string;
    liveThreads: string;
    secondBrainProjects: string;
    activeNow: string;
    vectorDbStatus: string;
    autoEvolution: string;
    close: string;
  };
  newProject: {
    title: string;
    button: string;
    subtitle: string;
  };
  exportMarkdown: {
    title: string;
    button: string;
    downloadBtn: string;
    copyBtn: string;
  };
  aiActions: {
    summarize: string;
    naturalChat: string;
    codeGen: string;
    audit: string;
  };
  settings: {
    title: string;
    button: string;
    subtitle: string;
    tabs: {
      general: string;
      github: string;
      ai: string;
      interface: string;
      storage: string;
      system: string;
    };
    language: string;
    reasoningMode: string;
    explanationStyle: string;
    styleConcise: string;
    styleDetailed: string;
    showQuickChips: string;
    showQuickChipsDesc: string;
    zenMode: string;
    zenModeDesc: string;
    githubToken: string;
    githubTokenDesc: string;
    githubTokenPlaceholder: string;
    save: string;
    saved: string;
    clearStorage: string;
    clearStorageConfirm: string;
    storageCleared: string;
  };
  github: {
    title: string;
    subtitle: string;
    button: string;
    inputLabel: string;
    inputPlaceholder: string;
    fetchBtn: string;
    fetching: string;
    importBtn: string;
    downloadZip: string;
    viewOnGithub: string;
    stars: string;
    forks: string;
    language: string;
    branch: string;
    size: string;
    openIssues: string;
    importedSuccess: string;
    errorNotFound: string;
    repoDetails: string;
  };
  codeReview: {
    tabTitle: string;
    autoReviewBadge: string;
    overallScore: string;
    grade: string;
    performance: string;
    security: string;
    architecture: string;
    suggestions: string;
    noIssuesFound: string;
    critical: string;
    warning: string;
    optimization: string;
    applyFix: string;
    applied: string;
    reanalyze: string;
    analyzing: string;
    suggestedSolution: string;
    filterAll: string;
    securityScore: string;
    perfScore: string;
    viewInDrawer: string;
  };
  latencyDashboard: {
    title: string;
    button: string;
    subtitle: string;
    avgLatency: string;
    fastest: string;
    p95: string;
    totalRuns: string;
    timelineTitle: string;
    phasesTitle: string;
    modesTitle: string;
    ms: string;
    averageLine: string;
    recentExecutions: string;
    emptyRuns: string;
    refresh: string;
    simulateRun: string;
    close: string;
    filterMode: string;
    allModes: string;
    tokens: string;
    status: string;
    time: string;
  };
}

export const translations: Record<Language, Translations> = {
  ar: {
    appName: 'Code It Core',
    appSubtitle: 'منصة الذكاء الاصطناعي وهندسة النظم',
    projectSwitcher: 'المشروع المستهدف',
    active: 'نشط',
    connectedProjects: 'مشاريع Second Brain v4',
    hostTelemetry: 'قياسات المضيف ROBEN',
    hostStatus: 'متصل',
    connected: 'متصل',
    newChat: 'محادثة جديدة',
    clearChat: 'مسح المحادثة',
    clearChatConfirm: 'هل أنت متأكد من مسح كافة الرسائل في هذه المحادثة؟',
    exportChat: 'تصدير المحادثة (GFM)',
    chatHistory: 'سجل الجلسات',
    noHistory: 'لا يوجد جلسات سابقة',
    newProject: {
      title: 'مشروع جديد في Second Brain',
      button: '+ مشروع جديد',
      subtitle: 'ربط مجلد جديد أو خدمة ذكية بالنظام',
    },
    exportMarkdown: {
      title: 'تصدير الجلسة بصيغة GitHub Flavored Markdown',
      button: 'تصدير Markdown',
      downloadBtn: 'تحميل كملف .md',
      copyBtn: 'نسخ إلى الحافظة',
    },
    aiActions: {
      summarize: 'تلخيص الجلسة بالذكاء الاصطناعي',
      naturalChat: 'دردشة واستشارة طبيعية',
      codeGen: 'توليد كود ومعمارية',
      audit: 'فحص أمني وتدقيق',
    },
    modes: {
      title: 'نمط المعالجة الهندسي',
      fast: {
        label: 'توليد سريع',
        desc: 'استجابة برمجية فورية للمهام المباشرة',
      },
      advanced: {
        label: 'معماري متقدم',
        desc: 'تحليل هيكلي دقيق متعدد الخطوات',
      },
      security: {
        label: 'تدقيق أمني',
        desc: 'فحص ثغرات وتشفير وتحصين الاستدعاءات',
      },
    },
    input: {
      placeholder: 'اكتب تعليماتك أو اسحب الملفات البرمجية هنا... (Enter للإرسال، Shift+Enter لسطر جديد)',
      attach: 'إرفاق ملف',
      send: 'إرسال',
      generating: 'جاري المعالجة...',
      attachments: 'مرفقات',
      removeFile: 'إزالة الملف',
    },
    welcome: {
      title: 'مرحباً بك في وحدة الذكاء البرمجي Code It',
      subtitle: 'حلول هندسية متطورة، كتابة شفرات برمجية دقيقة، وتتبع لمراحل التفكير المعماري المنظم لمشاريعك.',
      prompts: [
        {
          title: 'مراقبة تدفق البيانات (Data Flow)',
          prompt: 'قم ببرمجة وظيفة للتحقق من كفاءة تدفق البيانات وتنبيه النظام عند حدوث أي خطأ برمجي مع Circuit Breaker لمشروع Rico.',
        },
        {
          title: 'تحسين استعلام SQL مركب',
          prompt: 'قم بتحسين استعلام SQL لجلب إحصائيات المعاملات المالية الشهرية للمستخدمين مع الفهارس المناسبة وCTE في Postgres.',
        },
        {
          title: 'بناء نظام مصادقة آمن بـ TS',
          prompt: 'قم بإنشاء وحدة Middleware في Express للتحقق من رموز JWT والحد من معدل الطلبات (Rate Limiting) لمشروع Lvyy.',
        },
        {
          title: 'فحص ثغرات التزامن (Concurrency)',
          prompt: 'اكتب كود بايثون لمعالجة العمليات المتزامنة مع قفل الحسابات لمنع ثغرات السحب المزدوج (Double Spending).',
        },
      ],
    },
    message: {
      agentPipeline: 'مسار وكلاء Second Brain v4 التنفيذي:',
      completedPhases: 'مراحل مكتملة',
      phases: {
        researcher: 'البحث الدلالي بالذاكرة',
        architect: 'التصميم المعماري',
        editor: 'تنفيذ الشفرة',
        tester: 'فحص الـ Self-Healing',
        memory: 'تسجيل التطور',
      },
      thinkingCompleted: 'مسار التفكير الهندسي المنجز:',
      thinkingActive: 'جاري التحليل واستنباط مسار التنفيذ...',
      generatingResponse: 'جاري صياغة الاستجابة الهيكلية وكتابة الكود...',
      copy: 'نسخ الرد',
      copied: 'تم النسخ',
      interactiveFile: 'ملف برمجي تفاعلي قابل للتشغيل والتعديل',
      inspectCode: 'استعراض واختبار الكود',
      projectBadge: 'مشروع',
    },
    drawer: {
      title: 'المعاينة البرمجية التفاعلية',
      codeTab: 'الشفرة البرمجية',
      outputTab: 'فحص Self-Healing',
      saveToProject: 'حفظ في المشروع',
      saving: 'جاري الحفظ...',
      saved: 'تم الحفظ في المشروع',
      runTest: 'تشغيل واختبار',
      testing: 'جاري الفحص...',
      copy: 'نسخ الكود',
      copied: 'تم نسخ الكود',
      download: 'تحميل كملف',
      lines: 'أسطر',
      bytes: 'بايت',
      targetProject: 'المسار المستهدف:',
      outputPlaceholder: 'انقر على "تشغيل واختبار" لتشغيل فاحص الـ Self-Healing في بيئة المضيف.',
    },
    telemetry: {
      title: 'قياسات نظام المضيف (Host Telemetry)',
      hostSpecs: 'ROBEN • متصل',
      cpu: 'المعالج (12 Cores)',
      cpuHot: 'تردد 3.4 GHz • Core 2 Hot',
      ram: 'الذاكرة (RAM)',
      ramOf: 'من',
      disk: 'القرص C:',
      diskFree: 'متبقي',
      coresLoad: 'توزيع الأحمال عبر أنوية المعالج (12 Cores)',
      liveThreads: 'خيوط معالجة نشطة (Live Threads)',
      secondBrainProjects: 'مشاريع Second Brain المرتبطة',
      activeNow: 'المشروع النشط:',
      vectorDbStatus: 'قاعدة بيانات Neon المتجهة (Vector DB) متصلة بـ 768-dim Embeddings',
      autoEvolution: 'التطور الذاتي نشط (Auto-Evolution)',
      close: 'إغلاق',
    },
    settings: {
      title: 'لوحة الضبط والإعدادات',
      button: 'الضبط',
      subtitle: 'تخصيص تفضيلات المنظومة، ربط GitHub، نمط الذكاء الاصطناعي وبساطة الواجهة',
      tabs: {
        general: 'عام',
        github: 'اتصال GitHub',
        ai: 'الذكاء الاصطناعي',
        interface: 'بساطة الواجهة',
        storage: 'الذاكرة والتخزين',
        system: 'بيئة المضيف',
      },
      language: 'لغة الواجهة والتخاطب',
      reasoningMode: 'نمط التفكير والمعالجة الافتراضي',
      explanationStyle: 'أسلوب الاستجابة والشرح',
      styleConcise: 'موجز وهندسي دقيق (Direct Engineering)',
      styleDetailed: 'تحليلي وتفصيلي (Comprehensive)',
      showQuickChips: 'إظهار أشرطة المساعدة والاختصارات السريعة',
      showQuickChipsDesc: 'قم بالتعطيل لجعل صفحة المحادثة أنظف وخالية من أي تشتيت',
      zenMode: 'نمط التركيز الهادئ (Zen Mode)',
      zenModeDesc: 'تبسيط الإطارات وزيادة المساحات الفارغة للتفاعل النقي',
      githubToken: 'رمز الوصول الشخصي (GitHub Personal Access Token)',
      githubTokenDesc: 'اختياري: يرفع حد طلبات الـ API إلى 5000 طلب/ساعة ويتيح استيراد المستودعات الخاصة',
      githubTokenPlaceholder: 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
      save: 'حفظ وتطبيق الإعدادات',
      saved: 'تم حفظ وتطبيق التفضيلات بنجاح',
      clearStorage: 'مسح التخزين المؤقت المحلي',
      clearStorageConfirm: 'سيتم مسح سجل الجلسات المخزنة محلياً وإعادة ضبط الإعدادات. هل تود الاستمرار؟',
      storageCleared: 'تم مسح التخزين المؤقت وإعادة الضبط بنجاح',
    },
    github: {
      title: 'ربط وتحميل من GitHub',
      subtitle: 'استيراد مستودع برمجي بالكامل وفحص ملفاته وربطه فوراً مع Second Brain',
      button: 'ربط GitHub',
      inputLabel: 'رابط المستودع أو اسم المالك/المشروع',
      inputPlaceholder: 'https://github.com/facebook/react أو owner/repo',
      fetchBtn: 'فحص المستودع',
      fetching: 'جارٍ الاستعلام من خوادم GitHub...',
      importBtn: 'استيراد كمشروع نشط في النظام',
      downloadZip: 'تحميل كملف مضغوط (ZIP)',
      viewOnGithub: 'عرض على GitHub ↗',
      stars: 'النجوم',
      forks: 'التفريعات',
      language: 'اللغة الأساسية',
      branch: 'الفرع الافتراضي',
      size: 'الحجم التقريبي',
      openIssues: 'المشكلات المفتوحة',
      importedSuccess: 'تم استيراد المستودع بنجاح وربطه كمشروع نشط في Second Brain!',
      errorNotFound: 'تعذر الوصول للمستودع. تأكد من صحة الرابط أو صلاحيات الوصول.',
      repoDetails: 'معلومات المستودع البرمجي',
    },
    codeReview: {
      tabTitle: 'مراجعة الكود والأمان',
      autoReviewBadge: 'مراجعة الكود التلقائية',
      overallScore: 'درجة التقييم الشاملة',
      grade: 'المستوى الهندسي',
      performance: 'تحسين الأداء والكفاءة',
      security: 'التدقيق الأمني والحماية',
      architecture: 'المعمارية والنظافة البرمجية',
      suggestions: 'الاقتراحات والتوصيات الهندسية',
      noIssuesFound: 'الكود متوافق مع أعلى معايير الجودة والأمان ولم يتم رصد أي ثغرات أو اختناقات في الأداء.',
      critical: 'حرج / أمني',
      warning: 'تنبيه أداء',
      optimization: 'تحسين مقترح',
      applyFix: 'تطبيق التعديل المقترح',
      applied: 'تم تطبيق التحسين',
      reanalyze: 'إعادة التدقيق والتحليل',
      analyzing: 'جاري فحص الكود بالذكاء الاصطناعي...',
      suggestedSolution: 'كود الحل المقترح:',
      filterAll: 'كافة الاقتراحات',
      securityScore: 'مؤشر الأمان',
      perfScore: 'مؤشر الأداء',
      viewInDrawer: 'فتح لوحة التدقيق المفصلة',
    },
    latencyDashboard: {
      title: 'لوحة قياسات زمن الاستجابة (Recharts)',
      button: 'مؤشرات الأداء وزمن الاستجابة',
      subtitle: 'مخططات تفاعلية دقيقة توضح سرعة المعالجة البرمجية وزمن الاستجابة لمراحل النظام',
      avgLatency: 'متوسط زمن الاستجابة',
      fastest: 'أسرع معالجة برمجية',
      p95: 'مؤشر P95 (الحد الأعلى)',
      totalRuns: 'إجمالي المعالجات المنفذة',
      timelineTitle: 'مخطط زمن الاستجابة التفاعلي (Latency Timeline)',
      phasesTitle: 'توزيع زمن مراحل معالجة الوكلاء (Agent Phases Latency)',
      modesTitle: 'مقارنة زمن الاستجابة حسب نمط التفكير (Latency by Reasoning Mode)',
      ms: 'مللي ثانية (ms)',
      averageLine: 'متوسط زمن الاستجابة',
      recentExecutions: 'سجل المعالجات البرمجية الأخيرة',
      emptyRuns: 'لم يتم تسجيل أي معالجات برمجية حتى الآن. أرسل أمراً لبدء القياس.',
      refresh: 'تحديث القياسات',
      simulateRun: 'محاكاة اختبار أداء',
      close: 'إغلاق',
      filterMode: 'تصفية حسب نمط التفكير:',
      allModes: 'كافة الأنماط',
      tokens: 'رمز (Tokens)',
      status: 'الحالة',
      time: 'الوقت',
    },
  },
  en: {
    appName: 'Code It Core',
    appSubtitle: 'AI Engineering & Systems Architecture',
    projectSwitcher: 'Target Project',
    active: 'Active',
    connectedProjects: 'Second Brain v4 Projects',
    hostTelemetry: 'ROBEN Host Telemetry',
    hostStatus: 'Connected',
    connected: 'Connected',
    newChat: 'New Session',
    clearChat: 'Clear Session',
    clearChatConfirm: 'Are you sure you want to clear all messages in this session?',
    exportChat: 'Export Session (GFM)',
    chatHistory: 'Sessions History',
    noHistory: 'No previous sessions',
    newProject: {
      title: 'New Second Brain Project',
      button: '+ New Project',
      subtitle: 'Connect a new directory or microservice',
    },
    exportMarkdown: {
      title: 'Export Session as GitHub Flavored Markdown',
      button: 'Export Markdown',
      downloadBtn: 'Download .md File',
      copyBtn: 'Copy to Clipboard',
    },
    aiActions: {
      summarize: 'Summarize Session with AI',
      naturalChat: 'Natural Consultation',
      codeGen: 'Code & Architecture',
      audit: 'Security & Audit',
    },
    modes: {
      title: 'Engineering Reasoning Mode',
      fast: {
        label: 'Fast Generate',
        desc: 'Instant code generation for direct implementation tasks',
      },
      advanced: {
        label: 'Architectural Deep Dive',
        desc: 'Multi-step structured architectural breakdown',
      },
      security: {
        label: 'Security Audit',
        desc: 'Vulnerability analysis, sanitization, and endpoint hardening',
      },
    },
    input: {
      placeholder: 'Type your instructions or drop code files here... (Enter to send, Shift+Enter for new line)',
      attach: 'Attach File',
      send: 'Send',
      generating: 'Processing...',
      attachments: 'attachments',
      removeFile: 'Remove file',
    },
    welcome: {
      title: 'Welcome to Code It Intelligence Console',
      subtitle: 'Advanced engineering workflows, precise multi-project code generation, and transparent reasoning pipelines.',
      prompts: [
        {
          title: 'Data Flow & Circuit Breaker',
          prompt: 'Program an asynchronous data pipeline verification function with automated error interception and Circuit Breaker pattern for Rico project.',
        },
        {
          title: 'Complex SQL Optimization',
          prompt: 'Optimize a complex PostgreSQL query for monthly user transaction analytics with composite indexing and CTEs.',
        },
        {
          title: 'Secure TS Authentication Middleware',
          prompt: 'Build an Express.js middleware for JWT signature validation, token expiry handling, and token bucket rate limiting for Lvyy project.',
        },
        {
          title: 'Concurrency & Race Condition Audit',
          prompt: 'Write Python concurrency code with row-level locks or distributed mutex to eliminate double-spending race conditions.',
        },
      ],
    },
    message: {
      agentPipeline: 'Second Brain v4 Multi-Agent Pipeline:',
      completedPhases: 'phases complete',
      phases: {
        researcher: 'Vector Memory Retrieval',
        architect: 'Architectural Design',
        editor: 'Code Implementation',
        tester: 'Self-Healing Test',
        memory: 'Evolution Logging',
      },
      thinkingCompleted: 'Engineering reasoning steps completed:',
      thinkingActive: 'Analyzing requirements and deducing execution strategy...',
      generatingResponse: 'Formulating structured response and writing production code...',
      copy: 'Copy Response',
      copied: 'Copied',
      interactiveFile: 'Interactive code artifact ready for inspection and execution',
      inspectCode: 'Inspect & Run Code',
      projectBadge: 'Project',
    },
    drawer: {
      title: 'Interactive Code Artifact',
      codeTab: 'Source Code',
      outputTab: 'Self-Healing Test',
      saveToProject: 'Save to Project',
      saving: 'Saving...',
      saved: 'Saved to Project',
      runTest: 'Run & Verify',
      testing: 'Testing...',
      copy: 'Copy Code',
      copied: 'Code Copied',
      download: 'Download File',
      lines: 'lines',
      bytes: 'bytes',
      targetProject: 'Target Path:',
      outputPlaceholder: 'Click "Run & Verify" to execute the self-healing test runner on the host environment.',
    },
    telemetry: {
      title: 'Host Telemetry & System Status',
      hostSpecs: 'ROBEN • Connected',
      cpu: 'Processor (12 Cores)',
      cpuHot: '3.4 GHz Base • Core 2 Hot',
      ram: 'Memory (RAM)',
      ramOf: 'of',
      disk: 'Drive C:',
      diskFree: 'free of',
      coresLoad: '12-Core Processor Load Distribution',
      liveThreads: 'Live Threads',
      secondBrainProjects: 'Connected Second Brain Projects',
      activeNow: 'Active Project:',
      vectorDbStatus: 'Neon Vector DB connected with 768-dim embeddings',
      autoEvolution: 'Auto-Evolution Active',
      close: 'Close',
    },
    settings: {
      title: 'System Settings & Preferences',
      button: 'Settings',
      subtitle: 'Customize platform preferences, GitHub connection, AI reasoning profile, and UI density',
      tabs: {
        general: 'General',
        github: 'GitHub Connection',
        ai: 'AI Engine',
        interface: 'UI Simplicity',
        storage: 'Memory & Cache',
        system: 'Host Info',
      },
      language: 'Console Language',
      reasoningMode: 'Default Reasoning Profile',
      explanationStyle: 'AI Explanation Style',
      styleConcise: 'Concise & Engineering Focused',
      styleDetailed: 'Comprehensive & Pedagogical',
      showQuickChips: 'Show Quick Action Chips',
      showQuickChipsDesc: 'Disable to keep the chat space completely calm and distraction-free',
      zenMode: 'Zen Minimal Mode',
      zenModeDesc: 'Streamlines card borders and expands negative space for pure interaction',
      githubToken: 'GitHub Personal Access Token (PAT)',
      githubTokenDesc: 'Optional: Boosts GitHub API rate limits to 5,000 req/hr and enables private repository access',
      githubTokenPlaceholder: 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
      save: 'Save Preferences',
      saved: 'Preferences applied successfully',
      clearStorage: 'Reset Local Cache',
      clearStorageConfirm: 'This will reset your local conversation cache and restore defaults. Continue?',
      storageCleared: 'Local cache cleared successfully',
    },
    github: {
      title: 'Connect & Import from GitHub',
      subtitle: 'Seamlessly link public or private repositories directly into Second Brain workspace',
      button: 'Connect GitHub',
      inputLabel: 'Repository URL or owner/repo shorthand',
      inputPlaceholder: 'https://github.com/facebook/react or owner/repo',
      fetchBtn: 'Fetch Repository',
      fetching: 'Querying GitHub API...',
      importBtn: 'Import as Active Project',
      downloadZip: 'Download Archive (ZIP)',
      viewOnGithub: 'View on GitHub ↗',
      stars: 'Stars',
      forks: 'Forks',
      language: 'Primary Language',
      branch: 'Default Branch',
      size: 'Code Size',
      openIssues: 'Open Issues',
      importedSuccess: 'Repository successfully imported as an active Second Brain project!',
      errorNotFound: 'Could not access repository. Verify the repository name or permissions.',
      repoDetails: 'Repository Overview',
    },
    codeReview: {
      tabTitle: 'Code Review & Security',
      autoReviewBadge: 'Automated Code Review',
      overallScore: 'Overall Quality Score',
      grade: 'Engineering Grade',
      performance: 'Performance Optimization',
      security: 'Security & Hardening',
      architecture: 'Clean Architecture & Style',
      suggestions: 'Recommendations & Audit Findings',
      noIssuesFound: 'Code adheres to production engineering standards with zero critical vulnerabilities or performance bottlenecks detected.',
      critical: 'Critical / Security',
      warning: 'Performance Warning',
      optimization: 'Optimization',
      applyFix: 'Apply Suggested Patch',
      applied: 'Patch Applied',
      reanalyze: 'Re-Analyze Code',
      analyzing: 'AI Auditor analyzing syntax and security...',
      suggestedSolution: 'Suggested Implementation:',
      filterAll: 'All Findings',
      securityScore: 'Security Score',
      perfScore: 'Performance Score',
      viewInDrawer: 'Open Full Code Audit',
    },
    latencyDashboard: {
      title: 'Response Latency Dashboard (Recharts)',
      button: 'Performance & Latency',
      subtitle: 'Interactive real-time telemetry metrics analyzing processing durations across pipeline phases',
      avgLatency: 'Average Latency',
      fastest: 'Fastest Run',
      p95: 'P95 Latency',
      totalRuns: 'Total Operations',
      timelineTitle: 'Response Latency Timeline (ms)',
      phasesTitle: 'Agent Phases Latency Breakdown',
      modesTitle: 'Latency Comparison by Reasoning Mode',
      ms: 'Milliseconds (ms)',
      averageLine: 'Average Latency Threshold',
      recentExecutions: 'Recent Code Executions Log',
      emptyRuns: 'No execution metrics recorded yet. Issue a command to initiate monitoring.',
      refresh: 'Refresh Metrics',
      simulateRun: 'Simulate Benchmark',
      close: 'Close',
      filterMode: 'Filter by Reasoning Mode:',
      allModes: 'All Profiles',
      tokens: 'Tokens',
      status: 'Status',
      time: 'Time',
    },
  },
};
