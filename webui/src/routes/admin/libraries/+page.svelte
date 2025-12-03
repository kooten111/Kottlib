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
    };
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
                    console.log(`Resuming progress monitoring for library ${library.id}`, progress);
                    scanProgress[library.id] = progress; // Set initial progress
                    scanningLibraries.add(library.id);
                    scanningLibraries = scanningLibraries; // Trigger reactivity
                    startProgressMonitoring(library.id);
                } else {
                    console.log(`No active scan for library ${library.id}`);
                }
            } catch (err) {
                console.error(`Failed to check scan progress for library ${library.id}:`, err);
            }
        }
    }

    function openCreateModal() {
        modalMode = "create";
        editingLibrary = null;
        formData = { name: "", path: "", scan_interval: 0 };
        saveError = null;
        showModal = true;
    }

    function openEditModal(library) {
        modalMode = "edit";
        editingLibrary = library;
        formData = {
            name: library.name,
            path: library.path,
            scan_interval: library.scan_interval || 0,
        };
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

            if (modalMode === "create") {
                const newLibrary = await createLibrary(formData);

                // Auto-start progress monitoring for new library
                scanningLibraries.add(newLibrary.id);
                scanningLibraries = scanningLibraries; // Trigger reactivity
                startProgressMonitoring(newLibrary.id);
            } else {
                await updateLibrary(editingLibrary.id, formData);
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
            const response = await fetch(`/v2/libraries/${libraryId}/scan/progress`);
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
            scanProgress[libraryId] = { current: 0, total: 0, message: "Starting scan...", in_progress: true };
        }

        // Poll for progress
        scanProgressIntervals[libraryId] = setInterval(async () => {
            const progress = await pollScanProgress(libraryId);

            if (progress && progress.in_progress) {
                // Enforce monotonic progress - never allow backwards movement
                const existingProgress = scanProgress[libraryId];
                if (existingProgress && progress.in_progress) {
                    // Only update if progress is moving forward or total changed
                    if (progress.current < existingProgress.current && progress.total === existingProgress.total) {
                        console.log(`[Progress] Ignoring backwards progress: ${progress.current} < ${existingProgress.current}`);
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
            } else {
                // No scan in progress - stop polling
                console.log(`No active scan for library ${libraryId}, stopping monitoring`);
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
                                        class="text-xl font-semibold text-dark-text"
                                    >
                                        {library.name}
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
                                            <div class="flex justify-between text-sm {scanProgress[library.id].in_progress ? 'text-dark-text-secondary' : 'text-accent-green font-medium'}">
                                                <span>{scanProgress[library.id].message}</span>
                                                {#if scanProgress[library.id].total > 0}
                                                    <span>{scanProgress[library.id].current} / {scanProgress[library.id].total}</span>
                                                {/if}
                                            </div>
                                            {#if scanProgress[library.id].total > 0}
                                                <div class="w-full bg-dark-bg-tertiary rounded-full h-2 overflow-hidden">
                                                    <div
                                                        class="bg-accent-green h-full transition-all duration-300"
                                                        style="width: {Math.min(100, (scanProgress[library.id].current / scanProgress[library.id].total) * 100)}%"
                                                    ></div>
                                                </div>
                                            {:else if scanProgress[library.id].in_progress}
                                                <div class="w-full bg-dark-bg-tertiary rounded-full h-2 overflow-hidden">
                                                    <div class="bg-accent-green h-full w-1/4 animate-pulse"></div>
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
                                        class="w-5 h-5 {scanningLibraries.has(library.id)
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
                    <label class="block text-sm font-medium text-dark-text mb-2"
                        >Library Name</label
                    >
                    <input
                        type="text"
                        bind:value={formData.name}
                        placeholder="e.g., Comics, Manga"
                        class="w-full bg-dark-bg-tertiary border border-gray-700 rounded-lg px-4 py-2 text-dark-text focus:ring-2 focus:ring-accent-orange focus:border-transparent outline-none transition-all"
                    />
                </div>

                <div>
                    <label class="block text-sm font-medium text-dark-text mb-2"
                        >Folder Path</label
                    >
                    <input
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
                    <label class="block text-sm font-medium text-dark-text mb-2"
                        >Scan Interval (minutes)</label
                    >
                    <input
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
