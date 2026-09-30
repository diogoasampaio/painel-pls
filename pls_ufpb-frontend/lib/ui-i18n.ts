export type UILocale = "en-US" | "pt-BR" | "es-ES" | "fr-FR"

export const UI_I18N: Record<
  UILocale,
  {
    dialog: { close: string; title: string }
    spinner: { loading: string }
    pagination: {
      navLabel: string
      previous: string
      next: string
      goToPrevious: string
      goToNext: string
      morePages: string
    }
    counter: { groupLabel: string; decrease: string; increase: string }
    command: {
      title: string
      description: string
      placeholder: string
      empty: string
    }
    selectList: { select: string; selected: string; clearSearch: string }
    inputPassword: { hide: string; show: string }
    progressCircular: { label: string }
    riskLevelBar: { value: string }
    headerSearch: { open: string; close: string }
    navDots: { sectionNav: string; goTo: string }
    footerMenu: { label: string }
    stepProgress: { label: string }
    combobox: {
      placeholder: string
      searchPlaceholder: string
      noResults: string
      noOptions: string
      clearSearch: string
      clearSelection: string
      clearAll: string
      selected: string
    }
    dashbox: { toolbar: Record<string, string>; status: Record<string, string> }
    dashrow: { resizePanels: string }
    treemap: { breadcrumb: string; explore: string }
    boxplot: {
      max: string
      q3: string
      median: string
      mean: string
      q1: string
      min: string
    }
    scatterChart: { rangeStart: string; rangeEnd: string }
    geomapChart: {
      zoomIn: string
      zoomOut: string
      resetZoom: string
      zoomControls: string
      expand: string
      collapse: string
      expandedTitle: string
    }
    candlestick: {
      open: string
      high: string
      low: string
      close: string
      volume: string
      bullish: string
      bearish: string
      ma: string
    }
    emptyState: { noData: string; dataWillAppear: string }
    cardStats: { thisPeriod: string; lastPeriod: string; noComparison: string }
    pieChart: { total: string }
    scoreRow: { loading: string; scoreLabel: string }
    searchBar: {
      placeholder: string
      label: string
      clear: string
      startVoice: string
      stopVoice: string
    }
    aiChat: {
      label: string
      placeholder: string
      send: string
      assistantName: string
      emptyTitle: string
      emptyDescription: string
    }
    modal: {
      confirm: string
      cancel: string
      minimize: string
      maximize: string
    }
    dataTable: {
      searchPlaceholder: string
      noData: string
      noDataDescription: string
      of: string
      rows: string
      rowsPerPage: string
      tableWithRows: string
    }
    pageLoader: { loading: string }
    pillGroup: { filterLabel: string }
    tabs: { tabList: string }
    toggleTheme: {
      light: string
      dark: string
      system: string
      trigger: string
    }
    scrollToTop: {
      label: string
      tooltip: string
    }
    carousel: {
      previous: string
      next: string
      slide: string
      goToSlide: string
      progress: string
    }
    badge: {
      remove: string
    }
    empty: {
      noData: string
      noDataDescription: string
      noResults: string
      noResultsDescription: string
      search: string
      searchDescription: string
      error: string
      errorDescription: string
    }
    switch: {
      toggle: string
    }
    accordion: {
      expand: string
      collapse: string
    }
    input: {
      clear: string
    }
    avatar: {
      online: string
      busy: string
      away: string
      offline: string
      more: string
    }
    select: {
      placeholder: string
      search: string
      noResults: string
      create: string
      selected: string
    }
    cardStatGauge: {
      poor: string
      fair: string
      good: string
      excellent: string
      noReading: string
      pending: string
    }
    cardStatHighlight: {
      noSpotlight: string
      spotlightDescription: string
    }
    cardStatList: {
      listEmpty: string
      listEmptyDescription: string
    }
    cardStat: {
      nothingToMeasure: string
    }
    cardStatSparkline: {
      noHistory: string
    }
    cardStatProgress: {
      noGoalSet: string
    }
    searchCombo: {
      placeholder: string
      label: string
      noResults: string
      clearSearch: string
      searchByVoice: string
      stopRecording: string
    }
    progressBar: {
      label: string
    }
    copyBlock: {
      copy: string
      copied: string
    }
    fileUpload: {
      dragDrop: string
      clickToBrowse: string
      maxSizeLabel: string
      uploading: string
      fileTooLargeLabel: string
      remove: string
    }
    datePicker: {
      placeholder: string
    }
    tagInput: {
      removeTag: string
      addTag: string
      maxReached: string
    }
    phoneInput: {
      searchCountry: string
      noCountryFound: string
    }
    filterBuilder: {
      selectField: string
      operator: string
      value: string
      valuePlaceholder: string
      addRule: string
      removeRule: string
    }
    guidedTour: {
      skip: string
      previous: string
      next: string
      finish: string
    }
    notificationCenter: {
      title: string
      markAllAsRead: string
      empty: string
    }
    waitlistForm: {
      placeholder: string
      button: string
      success: string
      invalidEmail: string
    }
    contactForm: {
      name: string
      namePlaceholder: string
      email: string
      emailPlaceholder: string
      subject: string
      subjectPlaceholder: string
      message: string
      messagePlaceholder: string
      topic: string
      send: string
      sending: string
      success: string
      error: string
    }
    lightbox: {
      previous: string
      next: string
      of: string
      close: string
    }
    videoDialog: {
      playVideo: string
      close: string
    }
    officeLocations: {
      openNow: string
      closed: string
    }
    stickyFeatureList: {
      sectionNav: string
    }
    auth: {
      login: string
      signUp: string
      email: string
      emailPlaceholder: string
      password: string
      passwordPlaceholder: string
      name: string
      namePlaceholder: string
      rememberMe: string
      forgotPassword: string
      dontHaveAccount: string
      alreadyHaveAccount: string
      createAccount: string
      termsAgreement: string
      termsOfService: string
      privacyPolicy: string
      and: string
      orContinueWith: string
      continueWith: string
      passkey: string
      passkeyDescription: string
      sendMagicLink: string
      checkYourEmail: string
      magicLinkSent: string
      openEmailApp: string
      resendIn: string
      resendCode: string
      enterCode: string
      verify: string
      twoFactorTitle: string
      twoFactorDescription: string
      useAlternativeMethod: string
      resetPasswordTitle: string
      resetPasswordDescription: string
      sendResetLink: string
      backToLogin: string
      resetLinkSent: string
      passwordStrengthWeak: string
      passwordStrengthMedium: string
      passwordStrengthStrong: string
      passwordStrengthVeryStrong: string
      ruleLength: string
      ruleUppercase: string
      ruleNumber: string
      ruleSpecial: string
    }
    snippet: {
      copy: string
      copied: string
      copyCode: string
    }
    contributionGraph: {
      less: string
      more: string
      noContributions: string
    }
    creditCard: {
      cardNumber: string
      cardHolder: string
      expiry: string
      cvc: string
    }
    stats: {
      title: string
      description: string
      trendUp: string
      trendDown: string
      period: string
    }
    team: {
      title: string
      description: string
      role: string
      joinTeam: string
      viewProfile: string
    }
    testimonials: {
      title: string
      description: string
      quote: string
      author: string
      role: string
    }
    timeline: {
      title: string
      description: string
      step: string
      now: string
    }
    pricing: {
      title: string
      description: string
      monthly: string
      yearly: string
      annual: string
      perMonth: string
      perYear: string
      billedMonthly: string
      billedAnnually: string
      save: string
      mostPopular: string
      getStarted: string
      contactSales: string
      freeTrial: string
      comparePlans: string
      feature: string
      features: string
      included: string
      notIncluded: string
    }
    billing: {
      nextBilling: string
      manage: string
      invoices: string
    }
    integrations: {
      title: string
      description: string
      searchPlaceholder: string
      noResults: string
      viewAll: string
      connected: string
      available: string
    }
    howItWorks: {
      title: string
      description: string
      step: string
    }
    faqs: {
      title: string
      description: string
      searchPlaceholder: string
      noResults: string
      noResultsDescription: string
      stillHaveQuestions: string
      contactUs: string
      viewAll: string
    }
    cta: {
      badge: string
      getStarted: string
      learnMore: string
      tryFree: string
      contactSales: string
      subscribe: string
      emailPlaceholder: string
      noSpam: string
      trustedBy: string
    }
    blog: {
      readMore: string
      readingTime: string
      publishedOn: string
      byAuthor: string
      category: string
      featured: string
      latest: string
      noPosts: string
      noPostsDescription: string
      searchPlaceholder: string
      filterByCategory: string
      allCategories: string
      viewAll: string
      minRead: string
    }
    banner: {
      dismiss: string
      announcement: string
      promotion: string
      cookieTitle: string
      cookieDescription: string
      acceptAll: string
      decline: string
      managePreferences: string
      learnMore: string
      appDownload: string
      newsletterTitle: string
      subscribe: string
      marqueeLabel: string
    }
    header: {
      menu: string
      closeMenu: string
      openMenu: string
      skipToContent: string
      toggleNav: string
      search: string
      notifications: string
      cart: string
      announcement: string
      dismissAnnouncement: string
    }
    footer: {
      newsletterTitle: string
      newsletterDescription: string
      newsletterPlaceholder: string
      subscribe: string
      subscribedSuccess: string
      privacyNotice: string
      allSystemsOperational: string
      degradedPerformance: string
      majorOutage: string
      underMaintenance: string
      uptime: string
      downloadOn: string
      appStore: string
      googlePlay: string
      getItOn: string
      webApp: string
      allRightsReserved: string
      privacyPolicy: string
      termsOfService: string
      cookiePolicy: string
      statusPage: string
    }
    about: {
      mission: string
      missionDescription: string
      vision: string
      visionDescription: string
      values: string
      ourStory: string
      ourJourney: string
      manifesto: string
      leadership: string
      culture: string
      readFounderLetter: string
      viewProjects: string
      learnMore: string
      milestones: string
      milestonesDescription: string
    }
    sidebar: {
      toggle: string
      search: string
      teams: string
      addTeam: string
      navigation: string
      documents: string
      more: string
    }
    teamSwitcher: {
      switchTeam: string
      teams: string
      addTeam: string
    }
    sidebarSearch: {
      placeholder: string
      label: string
    }
    sectionCards: {
      trendingUp: string
      trendingDown: string
    }
    authCard: {
      welcomeBack: string
      createAccount: string
      welcomeDescription: string
      createDescription: string
      noAccount: string
      hasAccount: string
      signIn: string
      signUp: string
    }
    dashboard: {
      documents: string
      searchPlaceholder: string
    }
    pageHeader: {
      back: string
      actions: string
    }
    dateRangePicker: {
      selectRange: string
      today: string
      yesterday: string
      last7Days: string
      last30Days: string
      thisMonth: string
      lastMonth: string
      customRange: string
      clear: string
    }
    inlineEdit: {
      clickToEdit: string
      save: string
      cancel: string
      saving: string
      placeholder: string
    }
    confirmDialog: {
      confirm: string
      cancel: string
      typeToConfirm: string
      confirmWord: string
    }
    activityFeed: {
      empty: string
      loading: string
      viewMore: string
      justNow: string
    }
    sparkline: {
      currentValue: string
    }
    transferList: {
      available: string
      selected: string
      searchPlaceholder: string
      moveRight: string
      moveLeft: string
      moveAllRight: string
      moveAllLeft: string
      noItems: string
    }
    metricComparison: {
      current: string
      previous: string
      increase: string
      decrease: string
      noChange: string
    }
    statusPage: {
      allOperational: string
      degradedPerformance: string
      partialOutage: string
      majorOutage: string
      uptime90Days: string
      today: string
      daysAgo90: string
      operational: string
      degraded: string
      outage: string
    }
    avatarPresence: {
      online: string
      offline: string
      busy: string
      away: string
    }
    skeletonLayout: {
      loading: string
    }
    shortcutSheet: {
      title: string
      description: string
      searchPlaceholder: string
      noShortcuts: string
      press: string
    }
    changelog: {
      latest: string
      viewDetails: string
      features: string
      fixes: string
      improvements: string
      breaking: string
    }
    featureSpotlight: {
      next: string
      previous: string
      gotIt: string
      dismiss: string
      step: string
      of: string
    }
    emptyAction: {
      primaryAction: string
      secondaryAction: string
      recommended: string
    }
    imageZoom: { alt: string }
  }
> = {
  "en-US": {
    dialog: { close: "Close", title: "Dialog" },
    spinner: { loading: "Loading" },
    pagination: {
      navLabel: "pagination",
      previous: "Previous",
      next: "Next",
      goToPrevious: "Go to previous page",
      goToNext: "Go to next page",
      morePages: "More pages",
    },
    counter: {
      groupLabel: "Counter",
      decrease: "Decrease value",
      increase: "Increase value",
    },
    command: {
      title: "Command Palette",
      description: "Search for a command to run...",
      placeholder: "Type a command or search...",
      empty: "No results found.",
    },
    selectList: {
      select: "Select",
      selected: "Selected",
      clearSearch: "Clear search",
    },
    inputPassword: { hide: "Hide password", show: "Show password" },
    progressCircular: { label: "Progress" },
    riskLevelBar: { value: "Value" },
    headerSearch: { open: "Open search", close: "Close search" },
    navDots: { sectionNav: "Section navigation", goTo: "Go to" },
    footerMenu: { label: "Footer Navigation" },
    stepProgress: { label: "Progress" },
    combobox: {
      placeholder: "Select…",
      searchPlaceholder: "Search…",
      noResults: "No results.",
      noOptions: "No options available.",
      clearSearch: "Clear search",
      clearSelection: "Clear selection",
      clearAll: "Clear all",
      selected: "selected",
    },
    dashbox: {
      toolbar: {
        refresh: "Refresh",
        collapse: "Collapse",
        expand: "Expand",
        fullscreen: "Fullscreen",
        restore: "Restore",
      },
      status: {
        live: "Live",
        warning: "Warning",
        error: "Error",
        idle: "Idle",
      },
    },
    dashrow: { resizePanels: "Resize panels" },
    treemap: { breadcrumb: "Treemap breadcrumb", explore: "click to explore" },
    boxplot: {
      max: "Max",
      q3: "Q3",
      median: "Median",
      mean: "Mean",
      q1: "Q1",
      min: "Min",
    },
    scatterChart: { rangeStart: "Range start", rangeEnd: "Range end" },
    geomapChart: {
      zoomIn: "Zoom in",
      zoomOut: "Zoom out",
      resetZoom: "Reset zoom",
      zoomControls: "Map zoom controls",
      expand: "Expand map",
      collapse: "Collapse map",
      expandedTitle: "Expanded map",
    },
    candlestick: {
      open: "Open",
      high: "High",
      low: "Low",
      close: "Close",
      volume: "Volume",
      bullish: "Bullish",
      bearish: "Bearish",
      ma: "MA",
    },
    emptyState: {
      noData: "No data to display",
      dataWillAppear: "Data will appear here once available.",
    },
    cardStats: {
      thisPeriod: "This period",
      lastPeriod: "Last period",
      noComparison: "No comparison data",
    },
    pieChart: { total: "Total" },
    scoreRow: { loading: "Loading", scoreLabel: "Score" },
    searchBar: {
      placeholder: "Search…",
      label: "Search",
      clear: "Clear search",
      startVoice: "Search by voice",
      stopVoice: "Stop recording",
    },
    aiChat: {
      label: "Chat conversation",
      placeholder: "Ask anything…",
      send: "Send message",
      assistantName: "Assistant",
      emptyTitle: "No messages yet",
      emptyDescription: "Start the conversation by sending a message below.",
    },
    modal: {
      confirm: "Confirm",
      cancel: "Cancel",
      minimize: "Minimize",
      maximize: "Maximize",
    },
    dataTable: {
      searchPlaceholder: "Search…",
      noData: "No data found",
      noDataDescription: "Data will appear here once available.",
      of: "of",
      rows: "rows",
      rowsPerPage: "Rows per page",
      tableWithRows: "Table with",
    },
    pageLoader: { loading: "Loading…" },
    pillGroup: { filterLabel: "Filter by" },
    tabs: { tabList: "Tab list" },
    toggleTheme: {
      light: "Light",
      dark: "Dark",
      system: "System",
      trigger: "Toggle theme",
    },
    scrollToTop: {
      label: "Scroll to top",
      tooltip: "Back to top",
    },
    carousel: {
      previous: "Previous",
      next: "Next",
      slide: "Slide",
      goToSlide: "Go to slide",
      progress: "Progress",
    },
    badge: {
      remove: "Remove",
    },
    empty: {
      noData: "No data to display",
      noDataDescription: "Data will appear here once available.",
      noResults: "No results found",
      noResultsDescription: "Try adjusting your search or filters.",
      search: "Search",
      searchDescription: "Enter a term to search.",
      error: "Something went wrong",
      errorDescription: "Please try again later.",
    },
    switch: {
      toggle: "Toggle",
    },
    accordion: {
      expand: "Expand",
      collapse: "Collapse",
    },
    input: {
      clear: "Clear",
    },
    avatar: {
      online: "Online",
      busy: "Busy",
      away: "Away",
      offline: "Offline",
      more: "more",
    },
    select: {
      placeholder: "Select…",
      search: "Search…",
      noResults: "No results found.",
      create: "Create",
      selected: "selected",
    },
    cardStatGauge: {
      poor: "Poor",
      fair: "Fair",
      good: "Good",
      excellent: "Excellent",
      noReading: "No reading",
      pending: "Pending",
    },
    cardStatHighlight: {
      noSpotlight: "No spotlight yet",
      spotlightDescription: "Your headline KPI will appear here",
    },
    cardStatList: {
      listEmpty: "List is empty",
      listEmptyDescription: "Add metrics to start tracking",
    },
    cardStat: {
      nothingToMeasure: "Nothing to measure yet",
    },
    cardStatSparkline: {
      noHistory: "No history yet",
    },
    cardStatProgress: {
      noGoalSet: "No goal set yet",
    },
    searchCombo: {
      placeholder: "Search…",
      label: "Search",
      noResults: "No results found.",
      clearSearch: "Clear search",
      searchByVoice: "Search by voice",
      stopRecording: "Stop recording",
    },
    progressBar: {
      label: "Progress",
    },
    copyBlock: {
      copy: "Copy",
      copied: "Copied!",
    },
    fileUpload: {
      dragDrop: "Drag and drop the file here",
      clickToBrowse: "or click to select",
      maxSizeLabel: "Max size",
      uploading: "Uploading...",
      fileTooLargeLabel: "File size must be under",
      remove: "Remove file",
    },
    datePicker: {
      placeholder: "Select a date",
    },
    tagInput: {
      removeTag: "Remove tag",
      addTag: "Add tag",
      maxReached: "Maximum limit reached",
    },
    phoneInput: {
      searchCountry: "Search country...",
      noCountryFound: "No country found.",
    },
    filterBuilder: {
      selectField: "Select a field",
      operator: "Operator",
      value: "Value",
      valuePlaceholder: "Filter value",
      addRule: "Add rule",
      removeRule: "Remove rule",
    },
    guidedTour: {
      skip: "Skip",
      previous: "Previous",
      next: "Next",
      finish: "Finish",
    },
    notificationCenter: {
      title: "Notifications",
      markAllAsRead: "Mark all as read",
      empty: "No notifications",
    },
    waitlistForm: {
      placeholder: "Enter your email address...",
      button: "Join waitlist",
      success: "Thank you! You have been added to the waitlist.",
      invalidEmail: "Please enter a valid email address.",
    },
    contactForm: {
      name: "Name",
      namePlaceholder: "Your name",
      email: "Email",
      emailPlaceholder: "you@example.com",
      subject: "Subject",
      subjectPlaceholder: "How can we help?",
      message: "Message",
      messagePlaceholder: "Tell us more...",
      topic: "Topic",
      send: "Send message",
      sending: "Sending...",
      success: "Message sent! We'll get back to you soon.",
      error: "Something went wrong. Please try again.",
    },
    lightbox: {
      previous: "Previous image",
      next: "Next image",
      of: "of",
      close: "Close",
    },
    videoDialog: {
      playVideo: "Play video preview",
      close: "Close video",
    },
    officeLocations: {
      openNow: "Open now",
      closed: "Closed",
    },
    stickyFeatureList: {
      sectionNav: "Feature navigation",
    },
    auth: {
      login: "Log in",
      signUp: "Sign up",
      email: "Email",
      emailPlaceholder: "name@example.com",
      password: "Password",
      passwordPlaceholder: "Enter your password",
      name: "Full name",
      namePlaceholder: "John Doe",
      rememberMe: "Remember me",
      forgotPassword: "Forgot password?",
      dontHaveAccount: "Don't have an account?",
      alreadyHaveAccount: "Already have an account?",
      createAccount: "Create account",
      termsAgreement: "By clicking continue, you agree to our",
      termsOfService: "Terms of Service",
      privacyPolicy: "Privacy Policy",
      and: "and",
      orContinueWith: "Or continue with",
      continueWith: "Continue with",
      passkey: "Sign in with Passkey",
      passkeyDescription: "Use Touch ID, Face ID, or your security key",
      sendMagicLink: "Send Magic Link",
      checkYourEmail: "Check your email",
      magicLinkSent: "We sent a sign-in link to",
      openEmailApp: "Open email app",
      resendIn: "Resend in",
      resendCode: "Resend code",
      enterCode: "Enter verification code",
      verify: "Verify",
      twoFactorTitle: "Two-factor authentication",
      twoFactorDescription: "Enter the 6-digit code sent to your device",
      useAlternativeMethod: "Try another way",
      resetPasswordTitle: "Reset your password",
      resetPasswordDescription:
        "Enter your email address and we'll send you a link to reset your password",
      sendResetLink: "Send reset link",
      backToLogin: "Back to log in",
      resetLinkSent: "Instructions sent to your email",
      passwordStrengthWeak: "Weak",
      passwordStrengthMedium: "Medium",
      passwordStrengthStrong: "Strong",
      passwordStrengthVeryStrong: "Very strong",
      ruleLength: "At least 8 characters",
      ruleUppercase: "At least one uppercase letter",
      ruleNumber: "At least one number",
      ruleSpecial: "At least one special character",
    },
    snippet: {
      copy: "Copy",
      copied: "Copied!",
      copyCode: "Copy code",
    },
    contributionGraph: {
      less: "Less",
      more: "More",
      noContributions: "No contributions",
    },
    creditCard: {
      cardNumber: "Card number",
      cardHolder: "Card holder",
      expiry: "Expiry",
      cvc: "CVC",
    },
    stats: {
      title: "Stats",
      description: "Key metrics at a glance.",
      trendUp: "Up",
      trendDown: "Down",
      period: "vs last period",
    },
    team: {
      title: "Our team",
      description: "Meet the people behind the product.",
      role: "Role",
      joinTeam: "Join our team",
      viewProfile: "View profile",
    },
    testimonials: {
      title: "What people say",
      description: "Trusted by teams worldwide.",
      quote: "Quote",
      author: "Author",
      role: "Role",
    },
    timeline: {
      title: "Timeline",
      description: "Our journey so far.",
      step: "Step",
      now: "Now",
    },
    pricing: {
      title: "Pricing",
      description: "Simple, transparent pricing.",
      monthly: "Monthly",
      yearly: "Yearly",
      annual: "Annual",
      perMonth: "/month",
      perYear: "/year",
      billedMonthly: "Billed monthly",
      billedAnnually: "Billed annually",
      save: "Save",
      mostPopular: "Most popular",
      getStarted: "Get started",
      contactSales: "Contact sales",
      freeTrial: "Free trial",
      comparePlans: "Compare plans",
      feature: "Feature",
      features: "Features",
      included: "Included",
      notIncluded: "Not included",
    },
    billing: {
      nextBilling: "Next billing",
      manage: "Manage",
      invoices: "Invoices",
    },
    integrations: {
      title: "Integrations",
      description: "Connect with your favorite tools.",
      searchPlaceholder: "Search integrations...",
      noResults: "No integrations found",
      viewAll: "View all",
      connected: "Connected",
      available: "Available",
    },
    howItWorks: {
      title: "How it works",
      description: "Simple steps to get started.",
      step: "Step",
    },
    faqs: {
      title: "Frequently asked questions",
      description: "Quick answers to common questions.",
      searchPlaceholder: "Search questions...",
      noResults: "No results found",
      noResultsDescription: "Try different keywords.",
      stillHaveQuestions: "Still have questions?",
      contactUs: "Contact us",
      viewAll: "View all FAQs",
    },
    cta: {
      badge: "New",
      getStarted: "Get started",
      learnMore: "Learn more",
      tryFree: "Try free",
      contactSales: "Contact sales",
      subscribe: "Subscribe",
      emailPlaceholder: "Enter your email",
      noSpam: "No spam. Unsubscribe anytime.",
      trustedBy: "Trusted by",
    },
    blog: {
      readMore: "Read more",
      readingTime: "min read",
      publishedOn: "Published on",
      byAuthor: "By",
      category: "Category",
      featured: "Featured",
      latest: "Latest",
      noPosts: "No posts found",
      noPostsDescription: "Try adjusting your search or filter.",
      searchPlaceholder: "Search posts...",
      filterByCategory: "Filter by category",
      allCategories: "All",
      viewAll: "View all",
      minRead: "min",
    },
    header: {
      menu: "Menu",
      closeMenu: "Close menu",
      openMenu: "Open menu",
      skipToContent: "Skip to content",
      toggleNav: "Toggle navigation",
      search: "Search",
      notifications: "Notifications",
      cart: "Cart",
      announcement: "Announcement",
      dismissAnnouncement: "Dismiss announcement",
    },
    banner: {
      dismiss: "Dismiss",
      announcement: "Announcement",
      promotion: "Promotion",
      cookieTitle: "We use cookies",
      cookieDescription: "We use cookies to improve your experience.",
      acceptAll: "Accept all",
      decline: "Decline",
      managePreferences: "Manage preferences",
      learnMore: "Learn more",
      appDownload: "Download app",
      newsletterTitle: "Stay updated",
      subscribe: "Subscribe",
      marqueeLabel: "Highlights",
    },
    footer: {
      newsletterTitle: "Stay updated",
      newsletterDescription:
        "Subscribe to our newsletter for the latest updates, releases, and articles.",
      newsletterPlaceholder: "Enter your email address",
      subscribe: "Subscribe",
      subscribedSuccess: "Thank you for subscribing!",
      privacyNotice: "We respect your privacy. Unsubscribe at any time.",
      allSystemsOperational: "All systems operational",
      degradedPerformance: "Degraded performance",
      majorOutage: "Major outage",
      underMaintenance: "Under maintenance",
      uptime: "uptime",
      downloadOn: "Download on the",
      appStore: "App Store",
      googlePlay: "Google Play",
      getItOn: "Get it on",
      webApp: "Web App",
      allRightsReserved: "All rights reserved.",
      privacyPolicy: "Privacy Policy",
      termsOfService: "Terms of Service",
      cookiePolicy: "Cookie Policy",
      statusPage: "Status Page",
    },
    about: {
      mission: "Our Mission",
      missionDescription:
        "Empowering innovation through accessible, robust, and state-of-the-art software systems.",
      vision: "Our Vision",
      visionDescription:
        "To be a premier university laboratory connecting cutting-edge academic research with high-impact software design.",
      values: "Our Values",
      ourStory: "Our Story",
      ourJourney: "Our Journey",
      manifesto: "Our Manifesto",
      leadership: "Leadership",
      culture: "Laboratory Culture",
      readFounderLetter: "Read director's message",
      viewProjects: "Explore research projects",
      learnMore: "Learn more",
      milestones: "Milestones & Achievements",
      milestonesDescription:
        "Key moments that defined our growth and academic impact.",
    },
    sidebar: {
      toggle: "Toggle sidebar",
      search: "Search",
      teams: "Teams",
      addTeam: "Add team",
      navigation: "Navigation",
      documents: "Documents",
      more: "More",
    },
    teamSwitcher: {
      switchTeam: "Switch team",
      teams: "Teams",
      addTeam: "Add team",
    },
    sidebarSearch: {
      placeholder: "Search the docs...",
      label: "Search",
    },
    sectionCards: {
      trendingUp: "Trending up",
      trendingDown: "Trending down",
    },
    authCard: {
      welcomeBack: "Welcome back",
      createAccount: "Create account",
      welcomeDescription: "Login to your Acme Inc account",
      createDescription: "Enter your details to create an account",
      noAccount: "Don't have an account?",
      hasAccount: "Already have an account?",
      signIn: "Sign in",
      signUp: "Sign up",
    },
    dashboard: {
      documents: "Documents",
      searchPlaceholder: "Search...",
    },
    pageHeader: {
      back: "Back",
      actions: "Actions",
    },
    dateRangePicker: {
      selectRange: "Select a date range",
      today: "Today",
      yesterday: "Yesterday",
      last7Days: "Last 7 days",
      last30Days: "Last 30 days",
      thisMonth: "This month",
      lastMonth: "Last month",
      customRange: "Custom range",
      clear: "Clear",
    },
    inlineEdit: {
      clickToEdit: "Click to edit",
      save: "Save",
      cancel: "Cancel",
      saving: "Saving...",
      placeholder: "Click to add text...",
    },
    confirmDialog: {
      confirm: "Confirm",
      cancel: "Cancel",
      typeToConfirm: "Type {word} to confirm:",
      confirmWord: "DELETE",
    },
    activityFeed: {
      empty: "No recent activity",
      loading: "Loading activity...",
      viewMore: "View more activity",
      justNow: "Just now",
    },
    sparkline: {
      currentValue: "Current value",
    },
    transferList: {
      available: "Available items",
      selected: "Selected items",
      searchPlaceholder: "Search items...",
      moveRight: "Move selected right",
      moveLeft: "Move selected left",
      moveAllRight: "Move all right",
      moveAllLeft: "Move all left",
      noItems: "No items found",
    },
    metricComparison: {
      current: "Current",
      previous: "Previous",
      increase: "increase",
      decrease: "decrease",
      noChange: "no change",
    },
    statusPage: {
      allOperational: "All systems operational",
      degradedPerformance: "Degraded performance",
      partialOutage: "Partial system outage",
      majorOutage: "Major system outage",
      uptime90Days: "90 days ago",
      today: "Today",
      daysAgo90: "90 days ago",
      operational: "Operational",
      degraded: "Degraded",
      outage: "Outage",
    },
    avatarPresence: {
      online: "Online",
      offline: "Offline",
      busy: "Busy",
      away: "Away",
    },
    skeletonLayout: {
      loading: "Loading content...",
    },
    shortcutSheet: {
      title: "Keyboard Shortcuts",
      description: "Available keyboard shortcuts to speed up your workflow",
      searchPlaceholder: "Search shortcuts...",
      noShortcuts: "No shortcuts found",
      press: "Press",
    },
    changelog: {
      latest: "Latest release",
      viewDetails: "View details",
      features: "New Features",
      fixes: "Bug Fixes",
      improvements: "Improvements",
      breaking: "Breaking Changes",
    },
    featureSpotlight: {
      next: "Next",
      previous: "Previous",
      gotIt: "Got it",
      dismiss: "Dismiss",
      step: "Step",
      of: "of",
    },
    emptyAction: {
      primaryAction: "Get started",
      secondaryAction: "Learn more",
      recommended: "Recommended steps",
    },
    imageZoom: { alt: "Zoom image" },
  },
  "pt-BR": {
    dialog: { close: "Fechar", title: "Diálogo" },
    spinner: { loading: "Carregando" },
    pagination: {
      navLabel: "paginação",
      previous: "Anterior",
      next: "Próximo",
      goToPrevious: "Ir para página anterior",
      goToNext: "Ir para próxima página",
      morePages: "Mais páginas",
    },
    counter: {
      groupLabel: "Contador",
      decrease: "Diminuir valor",
      increase: "Aumentar valor",
    },
    command: {
      title: "Paleta de Comandos",
      description: "Pesquise um comando para executar...",
      placeholder: "Digite um comando ou pesquise...",
      empty: "Nenhum resultado encontrado.",
    },
    selectList: {
      select: "Selecionar",
      selected: "Selecionado",
      clearSearch: "Limpar pesquisa",
    },
    inputPassword: { hide: "Ocultar senha", show: "Exibir senha" },
    progressCircular: { label: "Progresso" },
    riskLevelBar: { value: "Valor" },
    headerSearch: { open: "Abrir pesquisa", close: "Fechar pesquisa" },
    navDots: { sectionNav: "Navegação de seção", goTo: "Ir para" },
    footerMenu: { label: "Navegação do Rodapé" },
    stepProgress: { label: "Progresso" },
    combobox: {
      placeholder: "Selecionar…",
      searchPlaceholder: "Pesquisar…",
      noResults: "Nenhum resultado.",
      noOptions: "Nenhuma opção disponível.",
      clearSearch: "Limpar pesquisa",
      clearSelection: "Limpar seleção",
      clearAll: "Limpar tudo",
      selected: "selecionado(s)",
    },
    dashbox: {
      toolbar: {
        refresh: "Atualizar",
        collapse: "Recolher",
        expand: "Expandir",
        fullscreen: "Tela Cheia",
        restore: "Restaurar",
      },
      status: {
        live: "Online",
        warning: "Alerta",
        error: "Erro",
        idle: "Inativo",
      },
    },
    dashrow: { resizePanels: "Redimensionar painéis" },
    treemap: {
      breadcrumb: "Navegação do Treemap",
      explore: "clique para explorar",
    },
    boxplot: {
      max: "Máx",
      q3: "Q3",
      median: "Mediana",
      mean: "Média",
      q1: "Q1",
      min: "Mín",
    },
    scatterChart: {
      rangeStart: "Início do intervalo",
      rangeEnd: "Fim do intervalo",
    },
    geomapChart: {
      zoomIn: "Aumentar zoom",
      zoomOut: "Diminuir zoom",
      resetZoom: "Restaurar zoom",
      zoomControls: "Controles de zoom do mapa",
      expand: "Expandir mapa",
      collapse: "Recolher mapa",
      expandedTitle: "Mapa expandido",
    },
    candlestick: {
      open: "Abertura",
      high: "Máxima",
      low: "Mínima",
      close: "Fechamento",
      volume: "Volume",
      bullish: "Alta",
      bearish: "Baixa",
      ma: "MM",
    },
    emptyState: {
      noData: "Nenhum dado disponível",
      dataWillAppear: "Os dados aparecerão aqui quando estiverem disponíveis.",
    },
    cardStats: {
      thisPeriod: "Este período",
      lastPeriod: "Período anterior",
      noComparison: "Sem dados de comparação",
    },
    pieChart: { total: "Total" },
    scoreRow: { loading: "Carregando", scoreLabel: "Pontuação" },
    searchBar: {
      placeholder: "Buscar…",
      label: "Buscar",
      clear: "Limpar busca",
      startVoice: "Buscar por voz",
      stopVoice: "Parar gravação",
    },
    aiChat: {
      label: "Conversa do chat",
      placeholder: "Pergunte alguma coisa…",
      send: "Enviar mensagem",
      assistantName: "Assistente",
      emptyTitle: "Nenhuma mensagem ainda",
      emptyDescription: "Inicie a conversa enviando uma mensagem abaixo.",
    },
    modal: {
      confirm: "Confirmar",
      cancel: "Cancelar",
      minimize: "Minimizar",
      maximize: "Maximizar",
    },
    dataTable: {
      searchPlaceholder: "Buscar…",
      noData: "Nenhum dado encontrado",
      noDataDescription:
        "Os dados aparecerão aqui quando estiverem disponíveis.",
      of: "de",
      rows: "linhas",
      rowsPerPage: "Linhas por página",
      tableWithRows: "Tabela com",
    },
    pageLoader: { loading: "Carregando…" },
    pillGroup: { filterLabel: "Filtrar por" },
    tabs: { tabList: "Lista de abas" },
    toggleTheme: {
      light: "Claro",
      dark: "Escuro",
      system: "Sistema",
      trigger: "Alternar tema",
    },
    scrollToTop: {
      label: "Voltar ao topo",
      tooltip: "Voltar ao topo",
    },
    carousel: {
      previous: "Anterior",
      next: "Próximo",
      slide: "Slide",
      goToSlide: "Ir para o slide",
      progress: "Progresso",
    },
    badge: {
      remove: "Remover",
    },
    empty: {
      noData: "Nenhum dado disponível",
      noDataDescription:
        "Os dados aparecerão aqui quando estiverem disponíveis.",
      noResults: "Nenhum resultado encontrado",
      noResultsDescription: "Tente ajustar sua pesquisa ou filtros.",
      search: "Buscar",
      searchDescription: "Digite um termo para buscar.",
      error: "Algo deu errado",
      errorDescription: "Tente novamente mais tarde.",
    },
    switch: {
      toggle: "Alternar",
    },
    accordion: {
      expand: "Expandir",
      collapse: "Recolher",
    },
    input: {
      clear: "Limpar",
    },
    avatar: {
      online: "Online",
      busy: "Ocupado",
      away: "Ausente",
      offline: "Offline",
      more: "mais",
    },
    select: {
      placeholder: "Selecionar…",
      search: "Pesquisar…",
      noResults: "Nenhum resultado encontrado.",
      create: "Criar",
      selected: "selecionado(s)",
    },
    cardStatGauge: {
      poor: "Ruim",
      fair: "Regular",
      good: "Bom",
      excellent: "Excelente",
      noReading: "Sem leitura",
      pending: "Pendente",
    },
    cardStatHighlight: {
      noSpotlight: "Nenhum destaque ainda",
      spotlightDescription: "Seu KPI principal aparecerá aqui",
    },
    cardStatList: {
      listEmpty: "Lista vazia",
      listEmptyDescription: "Adicione métricas para começar",
    },
    cardStat: {
      nothingToMeasure: "Nada a medir ainda",
    },
    cardStatSparkline: {
      noHistory: "Nenhum histórico ainda",
    },
    cardStatProgress: {
      noGoalSet: "Nenhuma meta definida",
    },
    searchCombo: {
      placeholder: "Pesquisar…",
      label: "Pesquisar",
      noResults: "Nenhum resultado encontrado.",
      clearSearch: "Limpar pesquisa",
      searchByVoice: "Pesquisar por voz",
      stopRecording: "Parar gravação",
    },
    progressBar: {
      label: "Progresso",
    },
    copyBlock: {
      copy: "Copiar",
      copied: "Copiado!",
    },
    fileUpload: {
      dragDrop: "Arraste e solte o arquivo aqui",
      clickToBrowse: "ou clique para selecionar",
      maxSizeLabel: "Tamanho máximo",
      uploading: "Enviando...",
      fileTooLargeLabel: "O arquivo deve ter no máximo",
      remove: "Remover arquivo",
    },
    datePicker: {
      placeholder: "Selecione uma data",
    },
    tagInput: {
      removeTag: "Remover tag",
      addTag: "Adicionar tag",
      maxReached: "Limite máximo atingido",
    },
    phoneInput: {
      searchCountry: "Buscar país...",
      noCountryFound: "País não encontrado.",
    },
    filterBuilder: {
      selectField: "Selecione um campo",
      operator: "Operador",
      value: "Valor",
      valuePlaceholder: "Valor do filtro",
      addRule: "Adicionar regra",
      removeRule: "Remover regra",
    },
    guidedTour: {
      skip: "Pular",
      previous: "Anterior",
      next: "Próximo",
      finish: "Concluir",
    },
    notificationCenter: {
      title: "Notificações",
      markAllAsRead: "Marcar lidas",
      empty: "Nenhuma notificação",
    },
    waitlistForm: {
      placeholder: "Digite seu e-mail...",
      button: "Entrar na lista",
      success: "Obrigado! Você foi adicionado à lista de espera.",
      invalidEmail: "Por favor, insira um e-mail válido.",
    },
    contactForm: {
      name: "Nome",
      namePlaceholder: "Seu nome",
      email: "E-mail",
      emailPlaceholder: "voce@exemplo.com",
      subject: "Assunto",
      subjectPlaceholder: "Como podemos ajudar?",
      message: "Mensagem",
      messagePlaceholder: "Conte mais detalhes...",
      topic: "Assunto",
      send: "Enviar mensagem",
      sending: "Enviando...",
      success: "Mensagem enviada! Retornaremos em breve.",
      error: "Algo deu errado. Por favor, tente novamente.",
    },
    lightbox: {
      previous: "Imagem anterior",
      next: "Próxima imagem",
      of: "de",
      close: "Fechar",
    },
    videoDialog: {
      playVideo: "Reproduzir vídeo de demonstração",
      close: "Fechar vídeo",
    },
    officeLocations: {
      openNow: "Aberto agora",
      closed: "Fechado",
    },
    stickyFeatureList: {
      sectionNav: "Navegação de recursos",
    },
    auth: {
      login: "Entrar",
      signUp: "Criar conta",
      email: "E-mail",
      emailPlaceholder: "seu.email@exemplo.com",
      password: "Senha",
      passwordPlaceholder: "Digite sua senha",
      name: "Nome completo",
      namePlaceholder: "Maria Silva",
      rememberMe: "Lembrar de mim",
      forgotPassword: "Esqueceu a senha?",
      dontHaveAccount: "Não tem uma conta?",
      alreadyHaveAccount: "Já possui uma conta?",
      createAccount: "Criar minha conta",
      termsAgreement: "Ao continuar, você concorda com nossos",
      termsOfService: "Termos de Serviço",
      privacyPolicy: "Política de Privacidade",
      and: "e",
      orContinueWith: "Ou continue com",
      continueWith: "Continuar com",
      passkey: "Entrar com Passkey",
      passkeyDescription: "Use Touch ID, Face ID ou sua chave de segurança",
      sendMagicLink: "Enviar Link de Acesso",
      checkYourEmail: "Verifique seu e-mail",
      magicLinkSent: "Enviamos um link de acesso para",
      openEmailApp: "Abrir aplicativo de e-mail",
      resendIn: "Reenviar em",
      resendCode: "Reenviar código",
      enterCode: "Digite o código de verificação",
      verify: "Verificar código",
      twoFactorTitle: "Autenticação em duas etapas",
      twoFactorDescription:
        "Digite o código de 6 dígitos enviado para seu dispositivo",
      useAlternativeMethod: "Usar outro método",
      resetPasswordTitle: "Recuperar sua senha",
      resetPasswordDescription:
        "Digite seu e-mail para receber as instruções de redefinição de senha",
      sendResetLink: "Enviar instruções",
      backToLogin: "Voltar para o login",
      resetLinkSent: "Instruções enviadas para seu e-mail",
      passwordStrengthWeak: "Fraca",
      passwordStrengthMedium: "Média",
      passwordStrengthStrong: "Forte",
      passwordStrengthVeryStrong: "Muito forte",
      ruleLength: "Mínimo de 8 caracteres",
      ruleUppercase: "Pelo menos uma letra maiúscula",
      ruleNumber: "Pelo menos um número",
      ruleSpecial: "Pelo menos um caractere especial",
    },
    snippet: {
      copy: "Copiar",
      copied: "Copiado!",
      copyCode: "Copiar código",
    },
    contributionGraph: {
      less: "Menos",
      more: "Mais",
      noContributions: "Sem contribuições",
    },
    creditCard: {
      cardNumber: "Número do cartão",
      cardHolder: "Titular",
      expiry: "Validade",
      cvc: "CVC",
    },
    stats: {
      title: "Métricas",
      description: "Principais indicadores.",
      trendUp: "Alta",
      trendDown: "Queda",
      period: "vs período anterior",
    },
    team: {
      title: "Nossa equipe",
      description: "Conheça quem faz acontecer.",
      role: "Cargo",
      joinTeam: "Junte-se a nós",
      viewProfile: "Ver perfil",
    },
    testimonials: {
      title: "O que dizem",
      description: "Confiado por equipes no mundo.",
      quote: "Depoimento",
      author: "Autor",
      role: "Cargo",
    },
    timeline: {
      title: "Linha do tempo",
      description: "Nossa jornada até aqui.",
      step: "Etapa",
      now: "Agora",
    },
    pricing: {
      title: "Preços",
      description: "Preços simples e transparentes.",
      monthly: "Mensal",
      yearly: "Anual",
      annual: "Anual",
      perMonth: "/mês",
      perYear: "/ano",
      billedMonthly: "Cobrado mensalmente",
      billedAnnually: "Cobrado anualmente",
      save: "Economize",
      mostPopular: "Mais popular",
      getStarted: "Começar",
      contactSales: "Fale com vendas",
      freeTrial: "Teste grátis",
      comparePlans: "Comparar planos",
      feature: "Recurso",
      features: "Recursos",
      included: "Incluso",
      notIncluded: "Não incluso",
    },
    billing: {
      nextBilling: "Próxima cobrança",
      manage: "Gerenciar",
      invoices: "Faturas",
    },
    integrations: {
      title: "Integrações",
      description: "Conecte suas ferramentas favoritas.",
      searchPlaceholder: "Buscar integrações...",
      noResults: "Nenhuma integração encontrada",
      viewAll: "Ver todas",
      connected: "Conectado",
      available: "Disponível",
    },
    howItWorks: {
      title: "Como funciona",
      description: "Passos simples para começar.",
      step: "Etapa",
    },
    faqs: {
      title: "Perguntas frequentes",
      description: "Respostas rápidas para dúvidas comuns.",
      searchPlaceholder: "Buscar perguntas...",
      noResults: "Nenhum resultado",
      noResultsDescription: "Tente outras palavras-chave.",
      stillHaveQuestions: "Ainda tem dúvidas?",
      contactUs: "Fale conosco",
      viewAll: "Ver todas",
    },
    cta: {
      badge: "Novo",
      getStarted: "Começar agora",
      learnMore: "Saiba mais",
      tryFree: "Teste grátis",
      contactSales: "Fale com vendas",
      subscribe: "Inscrever-se",
      emailPlaceholder: "Digite seu e-mail",
      noSpam: "Sem spam. Cancele quando quiser.",
      trustedBy: "Confiado por",
    },
    blog: {
      readMore: "Ler mais",
      readingTime: "min de leitura",
      publishedOn: "Publicado em",
      byAuthor: "Por",
      category: "Categoria",
      featured: "Destaque",
      latest: "Recentes",
      noPosts: "Nenhum post encontrado",
      noPostsDescription: "Tente ajustar sua busca ou filtro.",
      searchPlaceholder: "Buscar posts...",
      filterByCategory: "Filtrar por categoria",
      allCategories: "Todos",
      viewAll: "Ver todos",
      minRead: "min",
    },
    header: {
      menu: "Menu",
      closeMenu: "Fechar menu",
      openMenu: "Abrir menu",
      skipToContent: "Pular para o conteúdo",
      toggleNav: "Alternar navegação",
      search: "Buscar",
      notifications: "Notificações",
      cart: "Carrinho",
      announcement: "Anúncio",
      dismissAnnouncement: "Fechar anúncio",
    },
    banner: {
      dismiss: "Dispensar",
      announcement: "Anúncio",
      promotion: "Promoção",
      cookieTitle: "Usamos cookies",
      cookieDescription: "Usamos cookies para melhorar sua experiência.",
      acceptAll: "Aceitar todos",
      decline: "Recusar",
      managePreferences: "Gerenciar preferências",
      learnMore: "Saiba mais",
      appDownload: "Baixar app",
      newsletterTitle: "Fique atualizado",
      subscribe: "Inscrever-se",
      marqueeLabel: "Destaques",
    },
    footer: {
      newsletterTitle: "Fique atualizado",
      newsletterDescription:
        "Receba as novidades, lançamentos e artigos diretamente na sua caixa de entrada.",
      newsletterPlaceholder: "Digite seu e-mail",
      subscribe: "Inscrever-se",
      subscribedSuccess: "Obrigado por se inscrever!",
      privacyNotice: "Respeitamos sua privacidade. Cancele quando quiser.",
      allSystemsOperational: "Todos os sistemas operacionais",
      degradedPerformance: "Desempenho degradado",
      majorOutage: "Interrupção do serviço",
      underMaintenance: "Em manutenção programada",
      uptime: "de disponibilidade",
      downloadOn: "Baixar na",
      appStore: "App Store",
      googlePlay: "Google Play",
      getItOn: "Disponível no",
      webApp: "Web App",
      allRightsReserved: "Todos os direitos reservados.",
      privacyPolicy: "Política de Privacidade",
      termsOfService: "Termos de Serviço",
      cookiePolicy: "Política de Cookies",
      statusPage: "Página de Status",
    },
    about: {
      mission: "Nossa Missão",
      missionDescription:
        "Impulsionar a inovação através de soluções de software acessíveis, robustas e de alto nível de engenharia.",
      vision: "Nossa Visão",
      visionDescription:
        "Ser referência universitária nacional na união entre pesquisa acadêmica de excelência e design digital de precisão.",
      values: "Nossos Valores",
      ourStory: "Nossa História",
      ourJourney: "Nossa Trajetória",
      manifesto: "Nosso Manifesto",
      leadership: "Liderança",
      culture: "Cultura do Laboratório",
      readFounderLetter: "Mensagem da coordenação",
      viewProjects: "Conhecer projetos",
      learnMore: "Saiba mais",
      milestones: "Marcos e Conquistas",
      milestonesDescription:
        "Momentos decisivos que moldaram nossa evolução e impacto acadêmico.",
    },
    sidebar: {
      toggle: "Alternar barra lateral",
      search: "Buscar",
      teams: "Equipes",
      addTeam: "Adicionar equipe",
      navigation: "Navegação",
      documents: "Documentos",
      more: "Mais",
    },
    teamSwitcher: {
      switchTeam: "Trocar equipe",
      teams: "Equipes",
      addTeam: "Adicionar equipe",
    },
    sidebarSearch: {
      placeholder: "Buscar documentos...",
      label: "Buscar",
    },
    sectionCards: {
      trendingUp: "Em alta",
      trendingDown: "Em queda",
    },
    authCard: {
      welcomeBack: "Bem-vindo de volta",
      createAccount: "Criar conta",
      welcomeDescription: "Entre na sua conta",
      createDescription: "Preencha seus dados para criar uma conta",
      noAccount: "Não tem uma conta?",
      hasAccount: "Já possui uma conta?",
      signIn: "Entrar",
      signUp: "Cadastrar",
    },
    dashboard: {
      documents: "Documentos",
      searchPlaceholder: "Buscar...",
    },
    pageHeader: {
      back: "Voltar",
      actions: "Ações",
    },
    dateRangePicker: {
      selectRange: "Selecione um período",
      today: "Hoje",
      yesterday: "Ontem",
      last7Days: "Últimos 7 dias",
      last30Days: "Últimos 30 dias",
      thisMonth: "Este mês",
      lastMonth: "Mês passado",
      customRange: "Período personalizado",
      clear: "Limpar",
    },
    inlineEdit: {
      clickToEdit: "Clique para editar",
      save: "Salvar",
      cancel: "Cancelar",
      saving: "Salvando...",
      placeholder: "Clique para adicionar texto...",
    },
    confirmDialog: {
      confirm: "Confirmar",
      cancel: "Cancelar",
      typeToConfirm: "Digite {word} para confirmar:",
      confirmWord: "EXCLUIR",
    },
    activityFeed: {
      empty: "Nenhuma atividade recente",
      loading: "Carregando atividades...",
      viewMore: "Ver mais atividades",
      justNow: "Agora mesmo",
    },
    sparkline: {
      currentValue: "Valor atual",
    },
    transferList: {
      available: "Itens disponíveis",
      selected: "Itens selecionados",
      searchPlaceholder: "Buscar itens...",
      moveRight: "Mover selecionados para a direita",
      moveLeft: "Mover selecionados para a esquerda",
      moveAllRight: "Mover todos para a direita",
      moveAllLeft: "Mover todos para a esquerda",
      noItems: "Nenhum item encontrado",
    },
    metricComparison: {
      current: "Atual",
      previous: "Anterior",
      increase: "aumento",
      decrease: "redução",
      noChange: "sem alteração",
    },
    statusPage: {
      allOperational: "Todos os sistemas operacionais",
      degradedPerformance: "Desempenho degradado",
      partialOutage: "Interrupção parcial do sistema",
      majorOutage: "Interrupção crítica do sistema",
      uptime90Days: "90 dias atrás",
      today: "Hoje",
      daysAgo90: "90 dias atrás",
      operational: "Operacional",
      degraded: "Degradado",
      outage: "Interrupção",
    },
    avatarPresence: {
      online: "Online",
      offline: "Offline",
      busy: "Ocupado",
      away: "Ausente",
    },
    skeletonLayout: {
      loading: "Carregando conteúdo...",
    },
    shortcutSheet: {
      title: "Atalhos de Teclado",
      description:
        "Atalhos de teclado disponíveis para agilizar seu fluxo de trabalho",
      searchPlaceholder: "Buscar atalhos...",
      noShortcuts: "Nenhum atalho encontrado",
      press: "Pressione",
    },
    changelog: {
      latest: "Última versão",
      viewDetails: "Ver detalhes",
      features: "Novas Funcionalidades",
      fixes: "Correções",
      improvements: "Melhorias",
      breaking: "Mudanças Críticas",
    },
    featureSpotlight: {
      next: "Próximo",
      previous: "Anterior",
      gotIt: "Entendi",
      dismiss: "Dispensar",
      step: "Passo",
      of: "de",
    },
    emptyAction: {
      primaryAction: "Começar",
      secondaryAction: "Saiba mais",
      recommended: "Passos recomendados",
    },
    imageZoom: { alt: "Imagem ampliada" },
  },
  "es-ES": {
    dialog: { close: "Cerrar", title: "Diálogo" },
    spinner: { loading: "Cargando" },
    pagination: {
      navLabel: "paginación",
      previous: "Anterior",
      next: "Siguiente",
      goToPrevious: "Ir a página anterior",
      goToNext: "Ir a página siguiente",
      morePages: "Más páginas",
    },
    counter: {
      groupLabel: "Contador",
      decrease: "Disminuir valor",
      increase: "Aumentar valor",
    },
    command: {
      title: "Paleta de Comandos",
      description: "Busque un comando para ejecutar...",
      placeholder: "Escriba un comando o busque...",
      empty: "No se encontraron resultados.",
    },
    selectList: {
      select: "Seleccionar",
      selected: "Seleccionado",
      clearSearch: "Limpiar búsqueda",
    },
    inputPassword: { hide: "Ocultar contraseña", show: "Mostrar contraseña" },
    progressCircular: { label: "Progreso" },
    riskLevelBar: { value: "Valor" },
    headerSearch: { open: "Abrir búsqueda", close: "Cerrar búsqueda" },
    navDots: { sectionNav: "Navegación de sección", goTo: "Ir a" },
    footerMenu: { label: "Navegación del Pie" },
    stepProgress: { label: "Progreso" },
    combobox: {
      placeholder: "Seleccionar…",
      searchPlaceholder: "Buscar…",
      noResults: "Sin resultados.",
      noOptions: "No hay opciones disponibles.",
      clearSearch: "Limpiar búsqueda",
      clearSelection: "Limpiar selección",
      clearAll: "Limpiar todo",
      selected: "seleccionado(s)",
    },
    dashbox: {
      toolbar: {
        refresh: "Actualizar",
        collapse: "Colapsar",
        expand: "Expandir",
        fullscreen: "Pantalla Completa",
        restore: "Restaurar",
      },
      status: {
        live: "En Vivo",
        warning: "Advertencia",
        error: "Error",
        idle: "Inactivo",
      },
    },
    dashrow: { resizePanels: "Redimensionar paneles" },
    treemap: {
      breadcrumb: "Navegación del Treemap",
      explore: "clic para explorar",
    },
    boxplot: {
      max: "Máx",
      q3: "Q3",
      median: "Mediana",
      mean: "Media",
      q1: "Q1",
      min: "Mín",
    },
    scatterChart: { rangeStart: "Inicio del rango", rangeEnd: "Fin del rango" },
    geomapChart: {
      zoomIn: "Acercar",
      zoomOut: "Alejar",
      resetZoom: "Restablecer zoom",
      zoomControls: "Controles de zoom del mapa",
      expand: "Expandir mapa",
      collapse: "Contraer mapa",
      expandedTitle: "Mapa expandido",
    },
    candlestick: {
      open: "Apertura",
      high: "Máximo",
      low: "Mínimo",
      close: "Cierre",
      volume: "Volumen",
      bullish: "Alcista",
      bearish: "Bajista",
      ma: "MM",
    },
    emptyState: {
      noData: "Sin datos para mostrar",
      dataWillAppear: "Los datos aparecerán aquí cuando estén disponibles.",
    },
    cardStats: {
      thisPeriod: "Este período",
      lastPeriod: "Período anterior",
      noComparison: "Sin datos de comparación",
    },
    pieChart: { total: "Total" },
    scoreRow: { loading: "Cargando", scoreLabel: "Puntuación" },
    searchBar: {
      placeholder: "Buscar…",
      label: "Buscar",
      clear: "Limpiar búsqueda",
      startVoice: "Buscar por voz",
      stopVoice: "Detener grabación",
    },
    aiChat: {
      label: "Conversación del chat",
      placeholder: "Pregunta lo que quieras…",
      send: "Enviar mensaje",
      assistantName: "Asistente",
      emptyTitle: "Aún no hay mensajes",
      emptyDescription: "Inicia la conversación enviando un mensaje abajo.",
    },
    modal: {
      confirm: "Confirmar",
      cancel: "Cancelar",
      minimize: "Minimizar",
      maximize: "Maximizar",
    },
    dataTable: {
      searchPlaceholder: "Buscar…",
      noData: "Sin datos",
      noDataDescription: "Los datos aparecerán aquí cuando estén disponibles.",
      of: "de",
      rows: "filas",
      rowsPerPage: "Filas por página",
      tableWithRows: "Tabla con",
    },
    pageLoader: { loading: "Cargando…" },
    pillGroup: { filterLabel: "Filtrar por" },
    tabs: { tabList: "Lista de pestañas" },
    toggleTheme: {
      light: "Claro",
      dark: "Oscuro",
      system: "Sistema",
      trigger: "Cambiar tema",
    },
    scrollToTop: {
      label: "Volver arriba",
      tooltip: "Volver arriba",
    },
    carousel: {
      previous: "Anterior",
      next: "Siguiente",
      slide: "Diapositiva",
      goToSlide: "Ir a la diapositiva",
      progress: "Progreso",
    },
    badge: {
      remove: "Eliminar",
    },
    empty: {
      noData: "Sin datos para mostrar",
      noDataDescription: "Los datos aparecerán aquí cuando estén disponibles.",
      noResults: "Sin resultados",
      noResultsDescription: "Intente ajustar su búsqueda o filtros.",
      search: "Buscar",
      searchDescription: "Ingrese un término para buscar.",
      error: "Algo salió mal",
      errorDescription: "Intente de nuevo más tarde.",
    },
    switch: {
      toggle: "Alternar",
    },
    accordion: {
      expand: "Expandir",
      collapse: "Colapsar",
    },
    input: {
      clear: "Limpiar",
    },
    avatar: {
      online: "En línea",
      busy: "Ocupado",
      away: "Ausente",
      offline: "Desconectado",
      more: "más",
    },
    select: {
      placeholder: "Seleccionar…",
      search: "Buscar…",
      noResults: "Sin resultados.",
      create: "Crear",
      selected: "seleccionado(s)",
    },
    cardStatGauge: {
      poor: "Malo",
      fair: "Regular",
      good: "Bueno",
      excellent: "Excelente",
      noReading: "Sin lectura",
      pending: "Pendiente",
    },
    cardStatHighlight: {
      noSpotlight: "Sin destacado aún",
      spotlightDescription: "Su KPI principal aparecerá aquí",
    },
    cardStatList: {
      listEmpty: "Lista vacía",
      listEmptyDescription: "Agregue métricas para empezar",
    },
    cardStat: {
      nothingToMeasure: "Nada que medir aún",
    },
    cardStatSparkline: {
      noHistory: "Sin historial aún",
    },
    cardStatProgress: {
      noGoalSet: "Ninguna meta establecida",
    },
    searchCombo: {
      placeholder: "Buscar…",
      label: "Buscar",
      noResults: "Sin resultados.",
      clearSearch: "Limpiar búsqueda",
      searchByVoice: "Buscar por voz",
      stopRecording: "Detener grabación",
    },
    progressBar: {
      label: "Progreso",
    },
    copyBlock: {
      copy: "Copiar",
      copied: "¡Copiado!",
    },
    fileUpload: {
      dragDrop: "Arrastra y suelta el archivo aquí",
      clickToBrowse: "o haz clic para seleccionar",
      maxSizeLabel: "Tamaño máximo",
      uploading: "Subiendo...",
      fileTooLargeLabel: "El archivo debe tener como máximo",
      remove: "Eliminar archivo",
    },
    datePicker: {
      placeholder: "Seleccionar fecha",
    },
    tagInput: {
      removeTag: "Eliminar etiqueta",
      addTag: "Añadir etiqueta",
      maxReached: "Límite máximo alcanzado",
    },
    phoneInput: {
      searchCountry: "Buscar país...",
      noCountryFound: "País no encontrado.",
    },
    filterBuilder: {
      selectField: "Seleccione un campo",
      operator: "Operador",
      value: "Valor",
      valuePlaceholder: "Valor del filtro",
      addRule: "Añadir regla",
      removeRule: "Eliminar regla",
    },
    guidedTour: {
      skip: "Saltar",
      previous: "Anterior",
      next: "Siguiente",
      finish: "Finalizar",
    },
    notificationCenter: {
      title: "Notificaciones",
      markAllAsRead: "Marcar como leídas",
      empty: "No hay notificaciones",
    },
    waitlistForm: {
      placeholder: "Introduce tu correo electrónico...",
      button: "Unirse a la lista",
      success: "¡Gracias! Te has añadido a la lista de espera.",
      invalidEmail: "Por favor, introduce un correo válido.",
    },
    contactForm: {
      name: "Nombre",
      namePlaceholder: "Tu nombre",
      email: "Correo electrónico",
      emailPlaceholder: "tu@ejemplo.com",
      subject: "Asunto",
      subjectPlaceholder: "¿Cómo podemos ayudarte?",
      message: "Mensaje",
      messagePlaceholder: "Cuéntanos más...",
      topic: "Tema",
      send: "Enviar mensaje",
      sending: "Enviando...",
      success: "¡Mensaje enviado! Te responderemos pronto.",
      error: "Algo salió mal. Por favor, inténtalo de nuevo.",
    },
    lightbox: {
      previous: "Imagen anterior",
      next: "Siguiente imagen",
      of: "de",
      close: "Cerrar",
    },
    videoDialog: {
      playVideo: "Reproducir video de demostración",
      close: "Cerrar video",
    },
    officeLocations: {
      openNow: "Abierto ahora",
      closed: "Cerrado",
    },
    stickyFeatureList: {
      sectionNav: "Navegación de funciones",
    },
    auth: {
      login: "Iniciar sesión",
      signUp: "Registrarse",
      email: "Correo electrónico",
      emailPlaceholder: "nombre@ejemplo.com",
      password: "Contraseña",
      passwordPlaceholder: "Introduce tu contraseña",
      name: "Nombre completo",
      namePlaceholder: "Carlos Gómez",
      rememberMe: "Recordarme",
      forgotPassword: "¿Olvidaste tu contraseña?",
      dontHaveAccount: "¿No tienes una cuenta?",
      alreadyHaveAccount: "¿Ya tienes una cuenta?",
      createAccount: "Crear cuenta",
      termsAgreement: "Al continuar, aceptas nuestros",
      termsOfService: "Términos de servicio",
      privacyPolicy: "Política de privacidad",
      and: "y",
      orContinueWith: "O continúa con",
      continueWith: "Continuar con",
      passkey: "Iniciar con Passkey",
      passkeyDescription: "Usa Touch ID, Face ID o tu llave de seguridad",
      sendMagicLink: "Enviar enlace de acceso",
      checkYourEmail: "Revisa tu correo",
      magicLinkSent: "Hemos enviado un enlace de acceso a",
      openEmailApp: "Abrir aplicación de correo",
      resendIn: "Reenviar en",
      resendCode: "Reenviar código",
      enterCode: "Introduce el código de verificación",
      verify: "Verificar",
      twoFactorTitle: "Autenticación en dos pasos",
      twoFactorDescription:
        "Introduce el código de 6 dígitos enviado a tu dispositivo",
      useAlternativeMethod: "Probar otro método",
      resetPasswordTitle: "Recuperar contraseña",
      resetPasswordDescription:
        "Introduce tu correo para recibir las instrucciones de recuperación",
      sendResetLink: "Enviar enlace de recuperación",
      backToLogin: "Volver a iniciar sesión",
      resetLinkSent: "Instrucciones enviadas a tu correo",
      passwordStrengthWeak: "Débil",
      passwordStrengthMedium: "Media",
      passwordStrengthStrong: "Fuerte",
      passwordStrengthVeryStrong: "Muy fuerte",
      ruleLength: "Al menos 8 caracteres",
      ruleUppercase: "Al menos una letra mayúscula",
      ruleNumber: "Al menos un número",
      ruleSpecial: "Al menos un carácter especial",
    },
    snippet: {
      copy: "Copiar",
      copied: "¡Copiado!",
      copyCode: "Copiar código",
    },
    contributionGraph: {
      less: "Menos",
      more: "Más",
      noContributions: "Sin contribuciones",
    },
    creditCard: {
      cardNumber: "Número de tarjeta",
      cardHolder: "Titular",
      expiry: "Vencimiento",
      cvc: "CVC",
    },
    stats: {
      title: "Estadísticas",
      description: "Métricas clave.",
      trendUp: "Subida",
      trendDown: "Bajada",
      period: "vs período anterior",
    },
    team: {
      title: "Nuestro equipo",
      description: "Conoce al equipo.",
      role: "Rol",
      joinTeam: "Únete al equipo",
      viewProfile: "Ver perfil",
    },
    testimonials: {
      title: "Testimonios",
      description: "Confiado por equipos.",
      quote: "Cita",
      author: "Autor",
      role: "Rol",
    },
    timeline: {
      title: "Línea de tiempo",
      description: "Nuestro recorrido.",
      step: "Paso",
      now: "Ahora",
    },
    pricing: {
      title: "Precios",
      description: "Precios simples y transparentes.",
      monthly: "Mensual",
      yearly: "Anual",
      annual: "Anual",
      perMonth: "/mes",
      perYear: "/año",
      billedMonthly: "Facturado mensual",
      billedAnnually: "Facturado anual",
      save: "Ahorra",
      mostPopular: "Más popular",
      getStarted: "Empezar",
      contactSales: "Contactar ventas",
      freeTrial: "Prueba gratis",
      comparePlans: "Comparar planes",
      feature: "Característica",
      features: "Características",
      included: "Incluido",
      notIncluded: "No incluido",
    },
    billing: {
      nextBilling: "Próxima facturación",
      manage: "Gestionar",
      invoices: "Facturas",
    },
    integrations: {
      title: "Integraciones",
      description: "Conecta tus herramientas favoritas.",
      searchPlaceholder: "Buscar integraciones...",
      noResults: "No se encontraron integraciones",
      viewAll: "Ver todas",
      connected: "Conectado",
      available: "Disponible",
    },
    howItWorks: {
      title: "Cómo funciona",
      description: "Pasos simples para empezar.",
      step: "Paso",
    },
    faqs: {
      title: "Preguntas frecuentes",
      description: "Respuestas rápidas a dudas comunes.",
      searchPlaceholder: "Buscar preguntas...",
      noResults: "Sin resultados",
      noResultsDescription: "Prueba otras palabras clave.",
      stillHaveQuestions: "¿Aún tienes dudas?",
      contactUs: "Contáctanos",
      viewAll: "Ver todas",
    },
    cta: {
      badge: "Nuevo",
      getStarted: "Empezar",
      learnMore: "Saber más",
      tryFree: "Prueba gratis",
      contactSales: "Contactar ventas",
      subscribe: "Suscribirse",
      emailPlaceholder: "Introduce tu correo",
      noSpam: "Sin spam. Cancela cuando quieras.",
      trustedBy: "Confiado por",
    },
    blog: {
      readMore: "Leer más",
      readingTime: "min de lectura",
      publishedOn: "Publicado el",
      byAuthor: "Por",
      category: "Categoría",
      featured: "Destacado",
      latest: "Recientes",
      noPosts: "No se encontraron posts",
      noPostsDescription: "Intenta ajustar tu búsqueda o filtro.",
      searchPlaceholder: "Buscar posts...",
      filterByCategory: "Filtrar por categoría",
      allCategories: "Todos",
      viewAll: "Ver todos",
      minRead: "min",
    },
    header: {
      menu: "Menú",
      closeMenu: "Cerrar menú",
      openMenu: "Abrir menú",
      skipToContent: "Saltar al contenido",
      toggleNav: "Alternar navegación",
      search: "Buscar",
      notifications: "Notificaciones",
      cart: "Carrito",
      announcement: "Anuncio",
      dismissAnnouncement: "Cerrar anuncio",
    },
    banner: {
      dismiss: "Descartar",
      announcement: "Anuncio",
      promotion: "Promoción",
      cookieTitle: "Usamos cookies",
      cookieDescription: "Usamos cookies para mejorar tu experiencia.",
      acceptAll: "Aceptar todo",
      decline: "Rechazar",
      managePreferences: "Gestionar preferencias",
      learnMore: "Saber más",
      appDownload: "Descargar app",
      newsletterTitle: "Mantente actualizado",
      subscribe: "Suscribirse",
      marqueeLabel: "Destacados",
    },
    footer: {
      newsletterTitle: "Mantente al día",
      newsletterDescription:
        "Recibe las últimas novedades, lanzamientos y artículos directamente en tu correo.",
      newsletterPlaceholder: "Introduce tu correo",
      subscribe: "Suscribirse",
      subscribedSuccess: "¡Gracias por suscribirte!",
      privacyNotice: "Respetamos tu privacidad. Cancela cuando quieras.",
      allSystemsOperational: "Todos los sistemas operativos",
      degradedPerformance: "Rendimiento degradado",
      majorOutage: "Interrupción del servicio",
      underMaintenance: "En mantenimiento",
      uptime: "de disponibilidad",
      downloadOn: "Descargar en",
      appStore: "App Store",
      googlePlay: "Google Play",
      getItOn: "Disponible en",
      webApp: "Web App",
      allRightsReserved: "Todos los derechos reservados.",
      privacyPolicy: "Política de privacidad",
      termsOfService: "Términos de servicio",
      cookiePolicy: "Política de cookies",
      statusPage: "Página de estado",
    },
    about: {
      mission: "Nuestra Misión",
      missionDescription:
        "Impulsar la innovación mediante sistemas de software accesibles, robustos y de alta ingeniería.",
      vision: "Nuestra Visión",
      visionDescription:
        "Ser un laboratorio universitario de referencia que conecta la investigación de vanguardia con el diseño digital.",
      values: "Nuestros Valores",
      ourStory: "Nuestra Historia",
      ourJourney: "Nuestra Trayectoria",
      manifesto: "Nuestro Manifiesto",
      leadership: "Liderazgo",
      culture: "Cultura del Laboratorio",
      readFounderLetter: "Mensaje de la dirección",
      viewProjects: "Explorar proyectos",
      learnMore: "Saber más",
      milestones: "Hitos y Logros",
      milestonesDescription:
        "Momentos clave que definieron nuestro crecimiento e impacto.",
    },
    sidebar: {
      toggle: "Alternar barra lateral",
      search: "Buscar",
      teams: "Equipos",
      addTeam: "Añadir equipo",
      navigation: "Navegación",
      documents: "Documentos",
      more: "Más",
    },
    teamSwitcher: {
      switchTeam: "Cambiar equipo",
      teams: "Equipos",
      addTeam: "Añadir equipo",
    },
    sidebarSearch: {
      placeholder: "Buscar documentos...",
      label: "Buscar",
    },
    sectionCards: {
      trendingUp: "Tendencia alcista",
      trendingDown: "Tendencia bajista",
    },
    authCard: {
      welcomeBack: "Bienvenido de nuevo",
      createAccount: "Crear cuenta",
      welcomeDescription: "Inicia sesión en tu cuenta",
      createDescription: "Introduce tus datos para crear una cuenta",
      noAccount: "¿No tienes cuenta?",
      hasAccount: "¿Ya tienes cuenta?",
      signIn: "Iniciar sesión",
      signUp: "Registrarse",
    },
    dashboard: {
      documents: "Documentos",
      searchPlaceholder: "Buscar...",
    },
    pageHeader: {
      back: "Volver",
      actions: "Acciones",
    },
    dateRangePicker: {
      selectRange: "Seleccione un rango de fechas",
      today: "Hoy",
      yesterday: "Ayer",
      last7Days: "Últimos 7 días",
      last30Days: "Últimos 30 días",
      thisMonth: "Este mes",
      lastMonth: "Mes pasado",
      customRange: "Rango personalizado",
      clear: "Limpiar",
    },
    inlineEdit: {
      clickToEdit: "Haga clic para editar",
      save: "Guardar",
      cancel: "Cancelar",
      saving: "Guardando...",
      placeholder: "Haga clic para agregar texto...",
    },
    confirmDialog: {
      confirm: "Confirmar",
      cancel: "Cancelar",
      typeToConfirm: "Escriba {word} para confirmar:",
      confirmWord: "ELIMINAR",
    },
    activityFeed: {
      empty: "Sin actividad reciente",
      loading: "Cargando actividad...",
      viewMore: "Ver más actividad",
      justNow: "Ahora mismo",
    },
    sparkline: {
      currentValue: "Valor actual",
    },
    transferList: {
      available: "Elementos disponibles",
      selected: "Elementos seleccionados",
      searchPlaceholder: "Buscar elementos...",
      moveRight: "Mover seleccionados a la derecha",
      moveLeft: "Mover seleccionados a la izquierda",
      moveAllRight: "Mover todos a la derecha",
      moveAllLeft: "Mover todos a la izquierda",
      noItems: "No se encontraron elementos",
    },
    metricComparison: {
      current: "Actual",
      previous: "Anterior",
      increase: "incremento",
      decrease: "disminución",
      noChange: "sin cambios",
    },
    statusPage: {
      allOperational: "Todos los sistemas operacionales",
      degradedPerformance: "Rendimiento degradado",
      partialOutage: "Interrupción parcial del sistema",
      majorOutage: "Interrupción grave del sistema",
      uptime90Days: "Hace 90 días",
      today: "Hoy",
      daysAgo90: "Hace 90 días",
      operational: "Operacional",
      degraded: "Degradado",
      outage: "Interrupción",
    },
    avatarPresence: {
      online: "En línea",
      offline: "Desconectado",
      busy: "Ocupado",
      away: "Ausente",
    },
    skeletonLayout: {
      loading: "Cargando contenido...",
    },
    shortcutSheet: {
      title: "Atajos de Teclado",
      description:
        "Atajos de teclado disponibles para acelerar su flujo de trabajo",
      searchPlaceholder: "Buscar atajos...",
      noShortcuts: "No se encontraron atajos",
      press: "Presione",
    },
    changelog: {
      latest: "Última versión",
      viewDetails: "Ver detalles",
      features: "Nuevas Funciones",
      fixes: "Correcciones de Errores",
      improvements: "Mejoras",
      breaking: "Cambios Críticos",
    },
    featureSpotlight: {
      next: "Siguiente",
      previous: "Anterior",
      gotIt: "Entendido",
      dismiss: "Descartar",
      step: "Paso",
      of: "de",
    },
    emptyAction: {
      primaryAction: "Comenzar",
      secondaryAction: "Más información",
      recommended: "Pasos recomendados",
    },
    imageZoom: { alt: "Imagen ampliada" },
  },
  "fr-FR": {
    dialog: { close: "Fermer", title: "Dialogue" },
    spinner: { loading: "Chargement" },
    pagination: {
      navLabel: "pagination",
      previous: "Précédent",
      next: "Suivant",
      goToPrevious: "Aller à la page précédente",
      goToNext: "Aller à la page suivante",
      morePages: "Plus de pages",
    },
    counter: {
      groupLabel: "Compteur",
      decrease: "Diminuer la valeur",
      increase: "Augmenter la valeur",
    },
    command: {
      title: "Palette de Commandes",
      description: "Recherchez une commande à exécuter...",
      placeholder: "Tapez une commande ou recherchez...",
      empty: "Aucun résultat trouvé.",
    },
    selectList: {
      select: "Sélectionner",
      selected: "Sélectionné",
      clearSearch: "Effacer la recherche",
    },
    inputPassword: {
      hide: "Masquer le mot de passe",
      show: "Afficher le mot de passe",
    },
    progressCircular: { label: "Progression" },
    riskLevelBar: { value: "Valeur" },
    headerSearch: { open: "Ouvrir la recherche", close: "Fermer la recherche" },
    navDots: { sectionNav: "Navigation de section", goTo: "Aller à" },
    footerMenu: { label: "Navigation du Pied de Page" },
    stepProgress: { label: "Progression" },
    combobox: {
      placeholder: "Sélectionner…",
      searchPlaceholder: "Rechercher…",
      noResults: "Aucun résultat.",
      noOptions: "Aucune option disponible.",
      clearSearch: "Effacer la recherche",
      clearSelection: "Effacer la sélection",
      clearAll: "Tout effacer",
      selected: "sélectionné(s)",
    },
    dashbox: {
      toolbar: {
        refresh: "Actualiser",
        collapse: "Réduire",
        expand: "Agrandir",
        fullscreen: "Plein Écran",
        restore: "Restaurer",
      },
      status: {
        live: "En Direct",
        warning: "Avertissement",
        error: "Erreur",
        idle: "Inactif",
      },
    },
    dashrow: { resizePanels: "Redimensionner les panneaux" },
    treemap: {
      breadcrumb: "Navigation Treemap",
      explore: "cliquez pour explorer",
    },
    boxplot: {
      max: "Max",
      q3: "Q3",
      median: "Médiane",
      mean: "Moyenne",
      q1: "Q1",
      min: "Min",
    },
    scatterChart: {
      rangeStart: "Début de la plage",
      rangeEnd: "Fin de la plage",
    },
    geomapChart: {
      zoomIn: "Zoom avant",
      zoomOut: "Zoom arrière",
      resetZoom: "Réinitialiser le zoom",
      zoomControls: "Commandes de zoom de la carte",
      expand: "Agrandir la carte",
      collapse: "Réduire la carte",
      expandedTitle: "Carte agrandie",
    },
    candlestick: {
      open: "Ouverture",
      high: "Plus Haut",
      low: "Plus Bas",
      close: "Clôture",
      volume: "Volume",
      bullish: "Haussier",
      bearish: "Baissier",
      ma: "MM",
    },
    emptyState: {
      noData: "Aucune donnée à afficher",
      dataWillAppear:
        "Les données apparaîtront ici lorsqu'elles seront disponibles.",
    },
    cardStats: {
      thisPeriod: "Cette période",
      lastPeriod: "Période précédente",
      noComparison: "Aucune donnée de comparaison",
    },
    pieChart: { total: "Total" },
    scoreRow: { loading: "Chargement", scoreLabel: "Score" },
    searchBar: {
      placeholder: "Rechercher…",
      label: "Rechercher",
      clear: "Effacer la recherche",
      startVoice: "Rechercher par voix",
      stopVoice: "Arrêter l'enregistrement",
    },
    aiChat: {
      label: "Conversation du chat",
      placeholder: "Posez une question…",
      send: "Envoyer le message",
      assistantName: "Assistant",
      emptyTitle: "Pas encore de messages",
      emptyDescription:
        "Commencez la conversation en envoyant un message ci-dessous.",
    },
    modal: {
      confirm: "Confirmer",
      cancel: "Annuler",
      minimize: "Minimiser",
      maximize: "Maximiser",
    },
    dataTable: {
      searchPlaceholder: "Rechercher…",
      noData: "Aucune donnée",
      noDataDescription:
        "Les données apparaîtront ici lorsqu'elles seront disponibles.",
      of: "sur",
      rows: "lignes",
      rowsPerPage: "Lignes par page",
      tableWithRows: "Tableau avec",
    },
    pageLoader: { loading: "Chargement…" },
    pillGroup: { filterLabel: "Filtrer par" },
    tabs: { tabList: "Liste d'onglets" },
    toggleTheme: {
      light: "Clair",
      dark: "Sombre",
      system: "Système",
      trigger: "Changer de thème",
    },
    scrollToTop: {
      label: "Retour en haut",
      tooltip: "Retour en haut",
    },
    carousel: {
      previous: "Précédent",
      next: "Suivant",
      slide: "Diapositive",
      goToSlide: "Aller à la diapositive",
      progress: "Progression",
    },
    badge: {
      remove: "Supprimer",
    },
    empty: {
      noData: "Aucune donnée à afficher",
      noDataDescription:
        "Les données apparaîtront ici lorsqu'elles seront disponibles.",
      noResults: "Aucun résultat",
      noResultsDescription: "Essayez d'ajuster votre recherche ou vos filtres.",
      search: "Rechercher",
      searchDescription: "Entrez un terme de recherche.",
      error: "Une erreur est survenue",
      errorDescription: "Veuillez réessayer plus tard.",
    },
    switch: {
      toggle: "Basculer",
    },
    accordion: {
      expand: "Développer",
      collapse: "Réduire",
    },
    input: {
      clear: "Effacer",
    },
    avatar: {
      online: "En ligne",
      busy: "Occupé",
      away: "Absent",
      offline: "Hors ligne",
      more: "plus",
    },
    select: {
      placeholder: "Sélectionner…",
      search: "Rechercher…",
      noResults: "Aucun résultat.",
      create: "Créer",
      selected: "sélectionné(s)",
    },
    cardStatGauge: {
      poor: "Mauvais",
      fair: "Moyen",
      good: "Bon",
      excellent: "Excellent",
      noReading: "Aucune lecture",
      pending: "En attente",
    },
    cardStatHighlight: {
      noSpotlight: "Aucun point fort",
      spotlightDescription: "Votre KPI principal apparaîtra ici",
    },
    cardStatList: {
      listEmpty: "Liste vide",
      listEmptyDescription: "Ajoutez des métriques pour commencer",
    },
    cardStat: {
      nothingToMeasure: "Rien à mesurer",
    },
    cardStatSparkline: {
      noHistory: "Aucun historique",
    },
    cardStatProgress: {
      noGoalSet: "Aucun objectif défini",
    },
    searchCombo: {
      placeholder: "Rechercher…",
      label: "Rechercher",
      noResults: "Aucun résultat.",
      clearSearch: "Effacer la recherche",
      searchByVoice: "Rechercher par voix",
      stopRecording: "Arrêter l'enregistrement",
    },
    progressBar: {
      label: "Progression",
    },
    copyBlock: {
      copy: "Copier",
      copied: "Copié !",
    },
    fileUpload: {
      dragDrop: "Glissez-déposez le fichier ici",
      clickToBrowse: "ou cliquez pour sélectionner",
      maxSizeLabel: "Taille maximale",
      uploading: "Envoi en cours...",
      fileTooLargeLabel: "Le fichier doit faire au maximum",
      remove: "Supprimer le fichier",
    },
    datePicker: {
      placeholder: "Sélectionner une date",
    },
    tagInput: {
      removeTag: "Supprimer l'étiquette",
      addTag: "Ajouter une étiquette",
      maxReached: "Limite maximale atteinte",
    },
    phoneInput: {
      searchCountry: "Rechercher un pays...",
      noCountryFound: "Aucun pays trouvé.",
    },
    filterBuilder: {
      selectField: "Sélectionner un champ",
      operator: "Opérateur",
      value: "Valeur",
      valuePlaceholder: "Valeur du filtre",
      addRule: "Ajouter une règle",
      removeRule: "Supprimer la règle",
    },
    guidedTour: {
      skip: "Passer",
      previous: "Précédent",
      next: "Suivant",
      finish: "Terminer",
    },
    notificationCenter: {
      title: "Notifications",
      markAllAsRead: "Marquer tout comme lu",
      empty: "Aucune notification",
    },
    waitlistForm: {
      placeholder: "Entrez votre adresse email...",
      button: "Rejoindre la liste",
      success: "Merci! Vous avez été ajouté à la liste d'attente.",
      invalidEmail: "Veuillez entrer une adresse email valide.",
    },
    contactForm: {
      name: "Nom",
      namePlaceholder: "Votre nom",
      email: "E-mail",
      emailPlaceholder: "vous@exemple.com",
      subject: "Sujet",
      subjectPlaceholder: "Comment pouvons-nous vous aider ?",
      message: "Message",
      messagePlaceholder: "Dites-nous en plus...",
      topic: "Sujet",
      send: "Envoyer le message",
      sending: "Envoi en cours...",
      success: "Message envoyé ! Nous vous répondrons bientôt.",
      error: "Une erreur est survenue. Veuillez réessayer.",
    },
    lightbox: {
      previous: "Image précédente",
      next: "Image suivante",
      of: "sur",
      close: "Fermer",
    },
    videoDialog: {
      playVideo: "Lire la vidéo de démonstration",
      close: "Fermer la vidéo",
    },
    officeLocations: {
      openNow: "Ouvert maintenant",
      closed: "Fermé",
    },
    stickyFeatureList: {
      sectionNav: "Navigation des fonctionnalités",
    },
    auth: {
      login: "Se connecter",
      signUp: "Créer un compte",
      email: "E-mail",
      emailPlaceholder: "nom@exemple.com",
      password: "Mot de passe",
      passwordPlaceholder: "Entrez votre mot de passe",
      name: "Nom complet",
      namePlaceholder: "Claire Martin",
      rememberMe: "Se souvenir de moi",
      forgotPassword: "Mot de passe oublié ?",
      dontHaveAccount: "Vous n'avez pas de compte ?",
      alreadyHaveAccount: "Vous avez déjà un compte ?",
      createAccount: "Créer un compte",
      termsAgreement: "En continuant, vous acceptez nos",
      termsOfService: "Conditions d'utilisation",
      privacyPolicy: "Politique de confidentialité",
      and: "et",
      orContinueWith: "Ou continuer avec",
      continueWith: "Continuer avec",
      passkey: "Connexion avec Passkey",
      passkeyDescription: "Utilisez Touch ID, Face ID ou votre clé de sécurité",
      sendMagicLink: "Envoyer le lien magique",
      checkYourEmail: "Vérifiez vos e-mails",
      magicLinkSent: "Nous avons envoyé un lien de connexion à",
      openEmailApp: "Ouvrir l'application d'e-mail",
      resendIn: "Renvoyer dans",
      resendCode: "Renvoyer le code",
      enterCode: "Entrez le code de vérification",
      verify: "Vérifier",
      twoFactorTitle: "Authentification à deux facteurs",
      twoFactorDescription:
        "Entrez le code à 6 chiffres envoyé à votre appareil",
      useAlternativeMethod: "Essayer une autre méthode",
      resetPasswordTitle: "Réinitialiser votre mot de passe",
      resetPasswordDescription:
        "Entrez votre e-mail pour recevoir les instructions de réinitialisation",
      sendResetLink: "Envoyer les instructions",
      backToLogin: "Retour à la connexion",
      resetLinkSent: "Instructions envoyées à votre e-mail",
      passwordStrengthWeak: "Faible",
      passwordStrengthMedium: "Moyen",
      passwordStrengthStrong: "Fort",
      passwordStrengthVeryStrong: "Très fort",
      ruleLength: "Au moins 8 caractères",
      ruleUppercase: "Au moins une lettre majuscule",
      ruleNumber: "Au moins un chiffre",
      ruleSpecial: "Au moins un caractère spécial",
    },
    snippet: {
      copy: "Copier",
      copied: "Copié !",
      copyCode: "Copier le code",
    },
    contributionGraph: {
      less: "Moins",
      more: "Plus",
      noContributions: "Aucune contribution",
    },
    creditCard: {
      cardNumber: "Numéro de carte",
      cardHolder: "Titulaire",
      expiry: "Expiration",
      cvc: "CVC",
    },
    stats: {
      title: "Statistiques",
      description: "Indicateurs clés.",
      trendUp: "Hausse",
      trendDown: "Baisse",
      period: "vs période précédente",
    },
    team: {
      title: "Notre équipe",
      description: "Rencontrez l'équipe.",
      role: "Rôle",
      joinTeam: "Rejoignez-nous",
      viewProfile: "Voir le profil",
    },
    testimonials: {
      title: "Témoignages",
      description: "Approuvé par des équipes.",
      quote: "Citation",
      author: "Auteur",
      role: "Rôle",
    },
    timeline: {
      title: "Chronologie",
      description: "Notre parcours.",
      step: "Étape",
      now: "Maintenant",
    },
    pricing: {
      title: "Tarifs",
      description: "Tarifs simples et transparents.",
      monthly: "Mensuel",
      yearly: "Annuel",
      annual: "Annuel",
      perMonth: "/mois",
      perYear: "/an",
      billedMonthly: "Facturé mensuellement",
      billedAnnually: "Facturé annuellement",
      save: "Économisez",
      mostPopular: "Plus populaire",
      getStarted: "Commencer",
      contactSales: "Contacter les ventes",
      freeTrial: "Essai gratuit",
      comparePlans: "Comparer les plans",
      feature: "Fonctionnalité",
      features: "Fonctionnalités",
      included: "Inclus",
      notIncluded: "Non inclus",
    },
    billing: {
      nextBilling: "Prochaine facturation",
      manage: "Gérer",
      invoices: "Factures",
    },
    integrations: {
      title: "Intégrations",
      description: "Connectez vos outils préférés.",
      searchPlaceholder: "Rechercher...",
      noResults: "Aucune intégration trouvée",
      viewAll: "Voir tout",
      connected: "Connecté",
      available: "Disponible",
    },
    howItWorks: {
      title: "Comment ça marche",
      description: "Étapes simples pour commencer.",
      step: "Étape",
    },
    faqs: {
      title: "Questions fréquentes",
      description: "Réponses rapides aux questions courantes.",
      searchPlaceholder: "Rechercher...",
      noResults: "Aucun résultat",
      noResultsDescription: "Essayez d'autres mots-clés.",
      stillHaveQuestions: "Encore des questions ?",
      contactUs: "Nous contacter",
      viewAll: "Voir tout",
    },
    cta: {
      badge: "Nouveau",
      getStarted: "Commencer",
      learnMore: "En savoir plus",
      tryFree: "Essai gratuit",
      contactSales: "Contacter les ventes",
      subscribe: "S'abonner",
      emailPlaceholder: "Entrez votre e-mail",
      noSpam: "Pas de spam. Désabonnement à tout moment.",
      trustedBy: "Approuvé par",
    },
    blog: {
      readMore: "Lire plus",
      readingTime: "min de lecture",
      publishedOn: "Publié le",
      byAuthor: "Par",
      category: "Catégorie",
      featured: "À la une",
      latest: "Derniers",
      noPosts: "Aucun article trouvé",
      noPostsDescription: "Essayez d'ajuster votre recherche ou filtre.",
      searchPlaceholder: "Rechercher...",
      filterByCategory: "Filtrer par catégorie",
      allCategories: "Tous",
      viewAll: "Voir tout",
      minRead: "min",
    },
    header: {
      menu: "Menu",
      closeMenu: "Fermer le menu",
      openMenu: "Ouvrir le menu",
      skipToContent: "Aller au contenu",
      toggleNav: "Basculer la navigation",
      search: "Rechercher",
      notifications: "Notifications",
      cart: "Panier",
      announcement: "Annonce",
      dismissAnnouncement: "Fermer l'annonce",
    },
    banner: {
      dismiss: "Fermer",
      announcement: "Annonce",
      promotion: "Promotion",
      cookieTitle: "Nous utilisons des cookies",
      cookieDescription:
        "Nous utilisons des cookies pour améliorer votre expérience.",
      acceptAll: "Tout accepter",
      decline: "Refuser",
      managePreferences: "Gérer les préférences",
      learnMore: "En savoir plus",
      appDownload: "Télécharger l'app",
      newsletterTitle: "Restez informé",
      subscribe: "S'abonner",
      marqueeLabel: "À la une",
    },
    footer: {
      newsletterTitle: "Restez informé",
      newsletterDescription:
        "Abonnez-vous à notre newsletter pour recevoir les dernières actualités et mises à jour.",
      newsletterPlaceholder: "Entrez votre e-mail",
      subscribe: "S'abonner",
      subscribedSuccess: "Merci pour votre inscription !",
      privacyNotice:
        "Nous respectons votre vie privée. Désabonnez-vous à tout moment.",
      allSystemsOperational: "Tous les systèmes opérationnels",
      degradedPerformance: "Performances dégradées",
      majorOutage: "Panne majeure",
      underMaintenance: "En maintenance",
      uptime: "de disponibilité",
      downloadOn: "Télécharger sur",
      appStore: "App Store",
      googlePlay: "Google Play",
      getItOn: "Disponible sur",
      webApp: "Application Web",
      allRightsReserved: "Tous droits réservés.",
      privacyPolicy: "Politique de confidentialité",
      termsOfService: "Conditions d'utilisation",
      cookiePolicy: "Politique relative aux cookies",
      statusPage: "Page de statut",
    },
    about: {
      mission: "Notre Mission",
      missionDescription:
        "Favoriser l'innovation grâce à des systèmes logiciels accessibles, robustes et à la pointe de la technologie.",
      vision: "Notre Vision",
      visionDescription:
        "Être un laboratoire universitaire de premier plan alliant recherche d'excellence et design logiciel de précision.",
      values: "Nos Valeurs",
      ourStory: "Notre Histoire",
      ourJourney: "Notre Parcours",
      manifesto: "Notre Manifeste",
      leadership: "Direction",
      culture: "Culture du Laboratoire",
      readFounderLetter: "Message de la direction",
      viewProjects: "Découvrir les projets",
      learnMore: "En savoir plus",
      milestones: "Étapes et Réalisations",
      milestonesDescription:
        "Les moments clés qui ont forgé notre croissance et notre impact académique.",
    },
    sidebar: {
      toggle: "Basculer la barre latérale",
      search: "Rechercher",
      teams: "Équipes",
      addTeam: "Ajouter une équipe",
      navigation: "Navigation",
      documents: "Documents",
      more: "Plus",
    },
    teamSwitcher: {
      switchTeam: "Changer d'équipe",
      teams: "Équipes",
      addTeam: "Ajouter une équipe",
    },
    sidebarSearch: {
      placeholder: "Rechercher...",
      label: "Rechercher",
    },
    sectionCards: {
      trendingUp: "En hausse",
      trendingDown: "En baisse",
    },
    authCard: {
      welcomeBack: "Bon retour",
      createAccount: "Créer un compte",
      welcomeDescription: "Connectez-vous à votre compte",
      createDescription: "Saisissez vos informations pour créer un compte",
      noAccount: "Pas encore de compte ?",
      hasAccount: "Déjà un compte ?",
      signIn: "Se connecter",
      signUp: "S'inscrire",
    },
    dashboard: {
      documents: "Documents",
      searchPlaceholder: "Rechercher...",
    },
    pageHeader: {
      back: "Retour",
      actions: "Actions",
    },
    dateRangePicker: {
      selectRange: "Sélectionnez une période",
      today: "Aujourd'hui",
      yesterday: "Hier",
      last7Days: "7 derniers jours",
      last30Days: "30 derniers jours",
      thisMonth: "Ce mois-ci",
      lastMonth: "Mois dernier",
      customRange: "Période personnalisée",
      clear: "Effacer",
    },
    inlineEdit: {
      clickToEdit: "Cliquer pour modifier",
      save: "Enregistrer",
      cancel: "Annuler",
      saving: "Enregistrement...",
      placeholder: "Cliquer pour ajouter du texte...",
    },
    confirmDialog: {
      confirm: "Confirmer",
      cancel: "Annuler",
      typeToConfirm: "Tapez {word} pour confirmer :",
      confirmWord: "SUPPRIMER",
    },
    activityFeed: {
      empty: "Aucune activité récente",
      loading: "Chargement de l'activité...",
      viewMore: "Voir plus d'activités",
      justNow: "À l'instant",
    },
    sparkline: {
      currentValue: "Valeur actuelle",
    },
    transferList: {
      available: "Éléments disponibles",
      selected: "Éléments sélectionnés",
      searchPlaceholder: "Rechercher des éléments...",
      moveRight: "Déplacer la sélection à droite",
      moveLeft: "Déplacer la sélection à gauche",
      moveAllRight: "Tout déplacer à droite",
      moveAllLeft: "Tout déplacer à gauche",
      noItems: "Aucun élément trouvé",
    },
    metricComparison: {
      current: "Actuel",
      previous: "Précédent",
      increase: "augmentation",
      decrease: "diminution",
      noChange: "aucun changement",
    },
    statusPage: {
      allOperational: "Tous les systèmes sont opérationnels",
      degradedPerformance: "Performances dégradées",
      partialOutage: "Panne partielle du système",
      majorOutage: "Panne majeure du système",
      uptime90Days: "Il y a 90 jours",
      today: "Aujourd'hui",
      daysAgo90: "Il y a 90 jours",
      operational: "Opérationnel",
      degraded: "Dégradé",
      outage: "Panne",
    },
    avatarPresence: {
      online: "En ligne",
      offline: "Hors ligne",
      busy: "Occupé",
      away: "Absent",
    },
    skeletonLayout: {
      loading: "Chargement du contenu...",
    },
    shortcutSheet: {
      title: "Raccourcis Clavier",
      description:
        "Raccourcis clavier disponibles pour accélérer votre travail",
      searchPlaceholder: "Rechercher des raccourcis...",
      noShortcuts: "Aucun raccourci trouvé",
      press: "Appuyez sur",
    },
    changelog: {
      latest: "Dernière version",
      viewDetails: "Voir les détails",
      features: "Nouvelles Fonctionnalités",
      fixes: "Corrections de bugs",
      improvements: "Améliorations",
      breaking: "Changements majeurs",
    },
    featureSpotlight: {
      next: "Suivant",
      previous: "Précédent",
      gotIt: "Compris",
      dismiss: "Ignorer",
      step: "Étape",
      of: "sur",
    },
    emptyAction: {
      primaryAction: "Commencer",
      secondaryAction: "En savoir plus",
      recommended: "Étapes recommandées",
    },
    imageZoom: { alt: "Image agrandie" },
  },
}

export type AbbrevScale = { threshold: number; divisor: number; suffix: string }

export const ABBREV_SCALES: Record<UILocale, AbbrevScale[]> = {
  "pt-BR": [
    { threshold: 1e12, divisor: 1e12, suffix: " tri" },
    { threshold: 1e9, divisor: 1e9, suffix: " bi" },
    { threshold: 1e6, divisor: 1e6, suffix: " mi" },
    { threshold: 1e3, divisor: 1e3, suffix: " mil" },
  ],
  "en-US": [
    { threshold: 1e12, divisor: 1e12, suffix: "T" },
    { threshold: 1e9, divisor: 1e9, suffix: "B" },
    { threshold: 1e6, divisor: 1e6, suffix: "M" },
    { threshold: 1e3, divisor: 1e3, suffix: "K" },
  ],
  "es-ES": [
    { threshold: 1e12, divisor: 1e12, suffix: " B" },
    { threshold: 1e9, divisor: 1e9, suffix: " M" },
    { threshold: 1e6, divisor: 1e6, suffix: " M" },
    { threshold: 1e3, divisor: 1e3, suffix: " K" },
  ],
  "fr-FR": [
    { threshold: 1e12, divisor: 1e12, suffix: " T" },
    { threshold: 1e9, divisor: 1e9, suffix: " Md" },
    { threshold: 1e6, divisor: 1e6, suffix: " M" },
    { threshold: 1e3, divisor: 1e3, suffix: " k" },
  ],
}
