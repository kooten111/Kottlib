<script>
    import { onMount } from "svelte";
    import Navbar from "$lib/components/layout/Navbar.svelte";
    import Card from "$lib/components/common/Card.svelte";
    import {
        getLibraries,
        createLibrary,
        updateLibrary,
        deleteLibrary,
        scanLibrary,
    } from "$lib/api/libraries";
    import {
        Database,
        Plus,
        Edit2,
        Trash2,
        Folder,
        X,
        Check,
        AlertCircle,
        RefreshCw,
    } from "lucide-svelte";

    let libraries = [];
    let isLoading = true;
    let error = null;

    // Modal state
    let showModal = false;
    let modalMode = "create"; // 'create' or 'edit'
    let editingLibrary = null;
    let formData = {
        name: "",
        path: "",
        scan_interval: 0,
        reader_defaults: null,
    };
    let showReaderSettings = false;
    let isSaving = false;
    let saveError = null;
    let scanningLibraries = new Set(); // Set of library IDs currently scanning
    let scanProgress = {}; // library_id -> {current, total, message}
    let scanProgressIntervals = {}; // library_id -> interval handle

    onMount(async () => {
        await loadLibraries();
        await checkForActiveScans();
    });

    async function loadLibraries() {
        try {
            isLoading = true;
            error = null;
            libraries = await getLibraries();
            isLoading = false;
        } catch (err) {
            console.error("Failed to load libraries:", err);
            error = err.message;
            isLoading = false;
        }
    }

    async function checkForActiveScans() {
        // Check all libraries for active scans when page loads
        for (const library of libraries) {
            try {
                const progress = await pollScanProgress(library.id);
                if (progress && progress.in_progress) {
                    // Found an active scan - start monitoring it

                    scanProgress[library.id] = progress; // Set initial progress
                    scanningLibraries.add(library.id);
                    scanningLibraries = scanningLibraries; // Trigger reactivity
                    startProgressMonitoring(library.id);
                } else {
                }
            } catch (err) {
                console.error(
                    `Failed to check scan progress for library ${library.id}:`,
                    err,
                );
            }
        }
    }

    function openCreateModal() {
        modalMode = "create";
        editingLibrary = null;
        formData = {
            name: "",
            path: "",
            scan_interval: 0,
            exclude_from_webui: false,
            reader_defaults: null,
        };
        showReaderSettings = false;
        saveError = null;
        showModal = true;
    }

    function openEditModal(library) {
        modalMode = "edit";
        editingLibrary = library;
        // Create a deep copy of reader_defaults if it exists
        const readerDefaults = library.settings?.reader_defaults 
            ? { ...library.settings.reader_defaults }
            : null;
        formData = {
            name: library.name,
            path: library.path,
            scan_interval: library.scan_interval || 0,
            exclude_from_webui: library.exclude_from_webui || false,
            reader_defaults: readerDefaults,
        };
        showReaderSettings = !!readerDefaults;
        saveError = null;
        showModal = true;
    }

    function closeModal() {
        showModal = false;
        editingLibrary = null;
        saveError = null;
    }

    async function handleSubmit() {
        if (!formData.name || !formData.path) {
            saveError = "Name and Path are required";
            return;
        }

        try {
            isSaving = true;
            saveError = null;

            // Prepare data for API
            const submitData = {
                name: formData.name,
                path: formData.path,
                scan_interval: formData.scan_interval,
                exclude_from_webui: formData.exclude_from_webui,
            };

            // Include reader defaults in settings if they exist
            if (formData.reader_defaults) {
                // Preserve existing settings and merge in reader_defaults
                if (modalMode === "edit" && editingLibrary?.settings) {
                    submitData.settings = { ...editingLibrary.settings };
                } else {
                    submitData.settings = {};
                }
                submitData.settings.reader_defaults = { ...formData.reader_defaults };
            } else if (modalMode === "edit" && editingLibrary?.settings) {
                // Preserve existing settings but remove reader_defaults if cleared
                submitData.settings = { ...editingLibrary.settings };
                delete submitData.settings.reader_defaults;
            }

            if (modalMode === "create") {
                const newLibrary = await createLibrary(submitData);

                // Auto-start progress monitoring for new library
                scanningLibraries.add(newLibrary.id);
                scanningLibraries = scanningLibraries; // Trigger reactivity
                startProgressMonitoring(newLibrary.id);
            } else {
                await updateLibrary(editingLibrary.id, submitData);
            }

            await loadLibraries();
            closeModal();
        } catch (err) {
            console.error("Failed to save library:", err);
            saveError = err.message || "Failed to save library";
        } finally {
            isSaving = false;
        }
    }

    // Default reader settings
    const defaultReaderSettings = {
        fitMode: 'fit-height',
        readingMode: 'single',
        readingDirection: 'ltr',
        preloadPages: 3,
        backgroundColor: '#1a1a1a',
        autoHideControls: true,
        autoHideDelay: 3000
    };

    function initializeReaderDefaults() {
        if (!formData.reader_defaults) {
            formData.reader_defaults = { ...defaultReaderSettings };
        }
        showReaderSettings = true;
    }

    function clearReaderDefaults() {
        formData.reader_defaults = null;
        showReaderSettings = false;
    }

    function updateReaderDefault(key, value) {
        if (!formData.reader_defaults) {
            formData.reader_defaults = { ...defaultReaderSettings };
        }
        // Create a new object to trigger reactivity
        formData.reader_defaults = {
            ...formData.reader_defaults,
            [key]: value
        };
    }

    async function handleDelete(library) {
        if (
            !confirm(
                `Are you sure you want to delete library "${library.name}"? This action cannot be undone.`,
            )
        ) {
            return;
        }

        try {
            await deleteLibrary(library.id);
            await loadLibraries();
        } catch (err) {
            console.error("Failed to delete library:", err);
            alert("Failed to delete library: " + err.message);
        }
    }

    async function pollScanProgress(libraryId) {
        try {
            const response = await fetch(
                `/v2/libraries/${libraryId}/scan/progress`,
            );
            if (response.ok) {
                return await response.json();
            }
        } catch (err) {
            console.error("Failed to poll scan progress:", err);
        }
        return null;
    }

    function startProgressMonitoring(libraryId) {
        // Clear any existing interval for this library
        if (scanProgressIntervals[libraryId]) {
            clearInterval(scanProgressIntervals[libraryId]);
        }

        // Initialize progress - use existing if available
        if (!scanProgress[libraryId]) {
            scanProgress[libraryId] = {
                current: 0,
                total: 0,
                message: "Starting scan...",
                in_progress: true,
            };
        }

        // Poll for progress
        scanProgressIntervals[libraryId] = setInterval(async () => {
            const progress = await pollScanProgress(libraryId);

            if (progress && progress.in_progress) {
                // Enforce monotonic progress - never allow backwards movement
                const existingProgress = scanProgress[libraryId];
                if (existingProgress && progress.in_progress) {
                    // Only update if progress is moving forward or total changed
                    if (
                        progress.current < existingProgress.current &&
                        progress.total === existingProgress.total
                    ) {
                        return; // Skip this update
                    }
                }

                scanProgress = { ...scanProgress, [libraryId]: progress };
            } else if (progress && !progress.in_progress) {
                // Scan completed - stop polling for this library
                clearInterval(scanProgressIntervals[libraryId]);
                delete scanProgressIntervals[libraryId];
                scanningLibraries.delete(libraryId);
                scanningLibraries = scanningLibraries; // Trigger reactivity

                scanProgress = { ...scanProgress, [libraryId]: progress };

                // Refresh library list immediately to show updated counts
                await loadLibraries();

                // Keep the completion message visible for 5 seconds
                setTimeout(() => {
                    delete scanProgress[libraryId];
                    scanProgress = scanProgress; // Trigger reactivity
                }, 5000);
                // No scan in progress - stop polling
                clearInterval(scanProgressIntervals[libraryId]);
                delete scanProgressIntervals[libraryId];
                scanningLibraries.delete(libraryId);
                scanningLibraries = scanningLibraries; // Trigger reactivity
            }
        }, 500);
    }

    async function handleScan(library) {
        try {
            scanningLibraries.add(library.id);
            scanningLibraries = scanningLibraries; // Trigger reactivity
            await scanLibrary(library.id);

            // Start progress monitoring
            startProgressMonitoring(library.id);
        } catch (err) {
            console.error("Failed to start scan:", err);
            alert("Failed to start scan: " + err.message);
            scanningLibraries.delete(library.id);
            scanningLibraries = scanningLibraries; // Trigger reactivity
        }
    }
</script>

<Navbar />

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Header -->
    <div class="flex justify-between items-center mb-8">
        <div>
            <h1
                class="text-3xl font-bold text-dark-text flex items-center gap-3"
            >
                <Database class="w-8 h-8" />
                Library Management
            </h1>
            <p class="mt-2 text-dark-text-secondary">
                Manage your comic libraries and storage locations
            </p>
        </div>
        <button
            on:click={openCreateModal}
            class="px-4 py-2 bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover transition-all duration-200 shadow-sm hover:shadow-md flex items-center gap-2"
        >
            <Plus class="w-5 h-5" />
            Add Library
        </button>
    </div>

    {#if isLoading}
        <div class="flex justify-center items-center py-12">
            <div
                class="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-orange"
            ></div>
        </div>
    {:else if error}
        <Card>
            <div class="text-center py-8">
                <AlertCircle class="w-12 h-12 text-status-error mx-auto mb-4" />
                <p class="text-status-error">{error}</p>
                <button
                    on:click={loadLibraries}
                    class="mt-4 px-4 py-2 bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover transition-all duration-200 shadow-sm hover:shadow-md"
                >
                    Retry
                </button>
            </div>
        </Card>
    {:else}
        <div class="grid gap-6">
            {#if libraries.length === 0}
                <Card>
                    <div class="text-center py-12 text-dark-text-secondary">
                        <Database class="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p class="text-lg font-medium">No libraries found</p>
                        <p class="mt-2 text-sm">
                            Create your first library to start organizing your
                            comics
                        </p>
                        <button
                            on:click={openCreateModal}
                            class="mt-6 px-4 py-2 bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover transition-all duration-200 shadow-sm hover:shadow-md inline-flex items-center gap-2"
                        >
                            <Plus class="w-4 h-4" />
                            Create Library
                        </button>
                    </div>
                </Card>
            {:else}
                {#each libraries as library}
                    <Card class="hover:border-gray-600 transition-colors">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start gap-4 flex-1">
                                <div
                                    class="p-3 bg-dark-bg-secondary rounded-lg"
                                >
                                    <Folder class="w-6 h-6 text-accent-blue" />
                                </div>
                                <div class="flex-1">
                                    <h3
                                        class="text-xl font-semibold text-dark-text flex items-center gap-2"
                                    >
                                        {library.name}
                                        {#if library.exclude_from_webui}
                                            <span
                                                class="px-2 py-0.5 rounded-full bg-dark-bg-tertiary text-xs text-dark-text-secondary border border-gray-700 font-normal flex items-center gap-1"
                                                title="Hidden from WebUI"
                                            >
                                                Hidden
                                            </span>
                                        {/if}
                                    </h3>
                                    <p
                                        class="text-dark-text-secondary font-mono text-sm mt-1"
                                    >
                                        {library.path}
                                    </p>
                                    <div
                                        class="flex gap-4 mt-3 text-sm text-dark-text-muted"
                                    >
                                        <span
                                            >{library.comic_count || 0} comics</span
                                        >
                                        <span
                                            >{library.folder_count || 0} folders</span
                                        >
                                        {#if library.last_scan_at}
                                            <span
                                                >Last scanned: {new Date(
                                                    library.last_scan_at * 1000,
                                                ).toLocaleDateString()}</span
                                            >
                                        {/if}
                                    </div>

                                    <!-- Progress Bar -->
                                    {#if scanProgress[library.id]}
                                        <div class="mt-4 space-y-2">
                                            <div
                                                class="flex justify-between text-sm {scanProgress[
                                                    library.id
                                                ].in_progress
                                                    ? 'text-dark-text-secondary'
                                                    : 'text-accent-green font-medium'}"
                                            >
                                                <span
                                                    >{scanProgress[library.id]
                                                        .message}</span
                                                >
                                                {#if scanProgress[library.id].total > 0}
                                                    <span
                                                        >{scanProgress[
                                                            library.id
                                                        ].current} / {scanProgress[
                                                            library.id
                                                        ].total}</span
                                                    >
                                                {/if}
                                            </div>
                                            {#if scanProgress[library.id].total > 0}
                                                <div
                                                    class="w-full bg-dark-bg-tertiary rounded-full h-2 overflow-hidden"
                                                >
                                                    <div
                                                        class="bg-accent-green h-full transition-all duration-300"
                                                        style="width: {Math.min(
                                                            100,
                                                            (scanProgress[
                                                                library.id
                                                            ].current /
                                                                scanProgress[
                                                                    library.id
                                                                ].total) *
                                                                100,
                                                        )}%"
                                                    ></div>
                                                </div>
                                            {:else if scanProgress[library.id].in_progress}
                                                <div
                                                    class="w-full bg-dark-bg-tertiary rounded-full h-2 overflow-hidden"
                                                >
                                                    <div
                                                        class="bg-accent-green h-full w-1/4 animate-pulse"
                                                    ></div>
                                                </div>
                                            {/if}
                                        </div>
                                    {/if}
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <button
                                    on:click={() => handleScan(library)}
                                    disabled={scanningLibraries.has(library.id)}
                                    class="p-2 text-dark-text-secondary hover:text-accent-green hover:bg-dark-bg-secondary rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    title="Scan Files"
                                >
                                    <RefreshCw
                                        class="w-5 h-5 {scanningLibraries.has(
                                            library.id,
                                        )
                                            ? 'animate-spin'
                                            : ''}"
                                    />
                                </button>
                                <button
                                    on:click={() => openEditModal(library)}
                                    class="p-2 text-dark-text-secondary hover:text-accent-blue hover:bg-dark-bg-secondary rounded-lg transition-colors"
                                    title="Edit Library"
                                >
                                    <Edit2 class="w-5 h-5" />
                                </button>
                                <button
                                    on:click={() => handleDelete(library)}
                                    class="p-2 text-dark-text-secondary hover:text-status-error hover:bg-dark-bg-secondary rounded-lg transition-colors"
                                    title="Delete Library"
                                >
                                    <Trash2 class="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                    </Card>
                {/each}
            {/if}
        </div>
    {/if}
</div>

<!-- Modal -->
{#if showModal}
    <div
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
    >
        <div
            class="bg-dark-bg-secondary rounded-xl shadow-xl w-full max-w-lg border border-gray-700"
        >
            <div
                class="flex justify-between items-center p-6 border-b border-gray-700"
            >
                <h2 class="text-xl font-semibold text-dark-text">
                    {modalMode === "create"
                        ? "Add New Library"
                        : "Edit Library"}
                </h2>
                <button
                    on:click={closeModal}
                    class="text-dark-text-secondary hover:text-dark-text transition-colors"
                >
                    <X class="w-6 h-6" />
                </button>
            </div>

            <div class="p-6 space-y-4">
                {#if saveError}
                    <div
                        class="bg-red-950/50 border border-red-900/50 rounded-lg p-4 flex items-start gap-3"
                    >
                        <AlertCircle
                            class="w-5 h-5 text-status-error flex-shrink-0 mt-0.5"
                        />
                        <p class="text-sm text-red-200">{saveError}</p>
                    </div>
                {/if}

                <div>
                    <label for="library-name" class="block text-sm font-medium text-dark-text mb-2"
                        >Library Name</label
                    >
                    <input
                        id="library-name"
                        type="text"
                        bind:value={formData.name}
                        placeholder="e.g., Comics, Manga"
                        class="w-full bg-dark-bg-tertiary border border-gray-700 rounded-lg px-4 py-2 text-dark-text focus:ring-2 focus:ring-accent-orange focus:border-transparent outline-none transition-all"
                    />
                </div>

                <div>
                    <label for="folder-path" class="block text-sm font-medium text-dark-text mb-2"
                        >Folder Path</label
                    >
                    <input
                        id="folder-path"
                        type="text"
                        bind:value={formData.path}
                        placeholder="/path/to/your/comics"
                        class="w-full bg-dark-bg-tertiary border border-gray-700 rounded-lg px-4 py-2 text-dark-text focus:ring-2 focus:ring-accent-orange focus:border-transparent outline-none transition-all"
                    />
                    <p class="mt-1 text-xs text-dark-text-secondary">
                        Absolute path to the directory containing your comics
                    </p>
                </div>

                <div>
                    <label for="scan-interval" class="block text-sm font-medium text-dark-text mb-2"
                        >Scan Interval (minutes)</label
                    >
                    <input
                        id="scan-interval"
                        type="number"
                        min="0"
                        bind:value={formData.scan_interval}
                        placeholder="0"
                        class="w-full bg-dark-bg-tertiary border border-gray-700 rounded-lg px-4 py-2 text-dark-text focus:ring-2 focus:ring-accent-orange focus:border-transparent outline-none transition-all"
                    />
                    <p class="mt-1 text-xs text-dark-text-secondary">
                        Set to 0 to disable periodic scanning
                    </p>
                </div>

                <div class="flex items-center gap-3 pt-2">
                    <input
                        type="checkbox"
                        id="exclude_from_webui"
                        bind:checked={formData.exclude_from_webui}
                        class="w-5 h-5 rounded border-gray-700 bg-dark-bg-tertiary text-accent-orange focus:ring-accent-orange"
                    />
                    <label
                        for="exclude_from_webui"
                        class="text-sm font-medium text-dark-text cursor-pointer"
                    >
                        Hide from WebUI
                        <span
                            class="block text-xs text-dark-text-secondary font-normal mt-0.5"
                        >
                            Library will still be accessible via Mobile API
                            (OPDS)
                        </span>
                    </label>
                </div>

                <!-- Reader Settings Section -->
                <div class="pt-4 border-t border-gray-700">
                    <div class="flex items-center justify-between mb-3">
                        <div>
                            <span class="block text-sm font-medium text-dark-text">
                                Default Reader Settings
                            </span>
                            <p class="text-xs text-dark-text-secondary mt-0.5">
                                Configure default reader settings for this library
                            </p>
                        </div>
                        {#if !showReaderSettings}
                            <button
                                type="button"
                                on:click={initializeReaderDefaults}
                                class="px-3 py-1.5 text-xs bg-dark-bg-tertiary border border-gray-700 rounded-lg text-dark-text hover:bg-gray-700 transition-colors"
                            >
                                Configure
                            </button>
                        {:else}
                            <button
                                type="button"
                                on:click={clearReaderDefaults}
                                class="px-3 py-1.5 text-xs bg-red-950/50 border border-red-900/50 rounded-lg text-red-200 hover:bg-red-900/50 transition-colors"
                            >
                                Clear
                            </button>
                        {/if}
                    </div>

                    {#if showReaderSettings && formData.reader_defaults}
                        <div class="space-y-3 bg-dark-bg-tertiary/50 rounded-lg p-4">
                            <!-- Fit Mode -->
                            <div>
                                <span class="block text-xs font-medium text-dark-text mb-1.5">
                                    Fit Mode
                                </span>
                                <div class="flex gap-2">
                                    {#each ['fit-width', 'fit-height', 'original'] as mode}
                                        <button
                                            type="button"
                                            on:click={() => updateReaderDefault('fitMode', mode)}
                                            class="px-3 py-1.5 text-xs rounded border transition-colors {formData.reader_defaults.fitMode === mode
                                                ? 'bg-accent-orange border-accent-orange text-white'
                                                : 'bg-dark-bg-secondary border-gray-700 text-dark-text-secondary hover:border-gray-600'}"
                                        >
                                            {mode === 'fit-width' ? 'Fit Width' : mode === 'fit-height' ? 'Fit Height' : 'Original'}
                                        </button>
                                    {/each}
                                </div>
                            </div>

                            <!-- Reading Mode -->
                            <div>
                                <span class="block text-xs font-medium text-dark-text mb-1.5">
                                    Reading Mode
                                </span>
                                <div class="flex gap-2">
                                    {#each ['single', 'double', 'continuous'] as mode}
                                        <button
                                            type="button"
                                            on:click={() => updateReaderDefault('readingMode', mode)}
                                            class="px-3 py-1.5 text-xs rounded border transition-colors {formData.reader_defaults.readingMode === mode
                                                ? 'bg-accent-orange border-accent-orange text-white'
                                                : 'bg-dark-bg-secondary border-gray-700 text-dark-text-secondary hover:border-gray-600'}"
                                        >
                                            {mode === 'single' ? 'Single' : mode === 'double' ? 'Double' : 'Continuous'}
                                        </button>
                                    {/each}
                                </div>
                            </div>

                            <!-- Reading Direction -->
                            <div>
                                <span class="block text-xs font-medium text-dark-text mb-1.5">
                                    Reading Direction
                                </span>
                                <div class="flex gap-2">
                                    {#each [{value: 'ltr', label: 'Left to Right'}, {value: 'rtl', label: 'Right to Left (Manga)'}] as option}
                                        <button
                                            type="button"
                                            on:click={() => updateReaderDefault('readingDirection', option.value)}
                                            class="px-3 py-1.5 text-xs rounded border transition-colors {formData.reader_defaults.readingDirection === option.value
                                                ? 'bg-accent-orange border-accent-orange text-white'
                                                : 'bg-dark-bg-secondary border-gray-700 text-dark-text-secondary hover:border-gray-600'}"
                                        >
                                            {option.label}
                                        </button>
                                    {/each}
                                </div>
                            </div>

                            <!-- Preload Pages -->
                            <div>
                                <label for="preload-pages" class="block text-xs font-medium text-dark-text mb-1.5">
                                    Preload Pages: {formData.reader_defaults.preloadPages}
                                </label>
                                <input
                                    id="preload-pages"
                                    type="range"
                                    min="0"
                                    max="5"
                                    step="1"
                                    value={formData.reader_defaults.preloadPages}
                                    on:input={(e) => updateReaderDefault('preloadPages', parseInt(e.target.value))}
                                    class="w-full"
                                />
                            </div>

                            <!-- Background Color -->
                            <div>
                                <span class="block text-xs font-medium text-dark-text mb-1.5">
                                    Background Color
                                </span>
                                <div class="flex gap-2">
                                    {#each ['#1a1a1a', '#000000', '#242424', '#333333', '#ffffff'] as color}
                                        <button
                                            type="button"
                                            on:click={() => updateReaderDefault('backgroundColor', color)}
                                            class="w-8 h-8 rounded border-2 transition-all {formData.reader_defaults.backgroundColor === color
                                                ? 'border-accent-orange scale-110'
                                                : 'border-gray-700 hover:border-gray-600'}"
                                            style="background-color: {color}"
                                        >
                                            {#if formData.reader_defaults.backgroundColor === color}
                                                <svg
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    width="16"
                                                    height="16"
                                                    viewBox="0 0 24 24"
                                                    fill="none"
                                                    stroke={color === '#ffffff' ? '#000000' : '#ffffff'}
                                                    stroke-width="3"
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    class="mx-auto"
                                                >
                                                    <polyline points="20 6 9 17 4 12" />
                                                </svg>
                                            {/if}
                                        </button>
                                    {/each}
                                </div>
                            </div>

                            <!-- Auto-hide Controls -->
                            <div class="flex items-center gap-2">
                                <input
                                    type="checkbox"
                                    id="autoHideControls"
                                    checked={formData.reader_defaults.autoHideControls}
                                    on:change={(e) => updateReaderDefault('autoHideControls', e.target.checked)}
                                    class="w-4 h-4 rounded border-gray-700 bg-dark-bg-secondary text-accent-orange focus:ring-accent-orange"
                                />
                                <label
                                    for="autoHideControls"
                                    class="text-xs text-dark-text cursor-pointer"
                                >
                                    Auto-hide Controls
                                </label>
                            </div>
                        </div>
                    {/if}
                </div>
            </div>

            <div
                class="flex justify-end gap-3 p-6 border-t border-gray-700 bg-dark-bg-tertiary/50 rounded-b-xl"
            >
                <button
                    on:click={closeModal}
                    class="px-4 py-2 text-dark-text hover:text-white transition-colors"
                >
                    Cancel
                </button>
                <button
                    on:click={handleSubmit}
                    disabled={isSaving}
                    class="px-4 py-2 bg-accent-orange text-white rounded-lg hover:bg-accent-orange-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all shadow-sm"
                >
                    {#if isSaving}
                        <div
                            class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"
                        ></div>
                        Saving...
                    {:else}
                        <Check class="w-4 h-4" />
                        {modalMode === "create"
                            ? "Create Library"
                            : "Save Changes"}
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}
