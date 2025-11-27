<script>
    import Navbar from "$lib/components/layout/Navbar.svelte";
    import ThemeSelector from "$lib/components/settings/ThemeSelector.svelte";
    import { Settings, Palette } from "lucide-svelte";
</script>

<svelte:head>
    <title>Settings - YACLib</title>
</svelte:head>

<div class="flex flex-col min-h-screen">
    <Navbar />

    <main class="flex-1 container mx-auto px-4 py-8 max-w-content">
        <!-- Page Header -->
        <div class="page-header">
            <div class="header-title-section">
                <div class="icon-wrapper">
                    <Settings class="w-8 h-8 text-accent-orange" />
                </div>
                <div>
                    <h1 class="page-title">Settings</h1>
                    <p class="page-subtitle">
                        Customize your YACLib experience
                    </p>
                </div>
            </div>
        </div>

        <!-- Settings Content -->
        <div class="settings-content">
            <!-- Theme Settings -->
            <section class="settings-section">
                <div class="section-header">
                    <Palette class="w-6 h-6 text-accent-orange" />
                    <h2 class="section-title">Appearance</h2>
                </div>
                <div class="section-body">
                    <ThemeSelector />
                </div>
            </section>

            <!-- Future settings sections can go here -->
        </div>
    </main>
</div>

<style>
    .page-header {
        margin-bottom: 2rem;
    }

    .header-title-section {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .icon-wrapper {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 56px;
        height: 56px;
        background: var(--color-secondary-bg);
        border-radius: 12px;
    }

    .page-title {
        font-size: 2rem;
        font-weight: 700;
        color: var(--color-text);
        margin: 0;
    }

    .page-subtitle {
        font-size: 0.875rem;
        color: var(--color-text-secondary);
        margin: 0.25rem 0 0 0;
    }

    .settings-content {
        display: flex;
        flex-direction: column;
        gap: 2rem;
    }

    .settings-section {
        padding: 2rem;
        background: var(--color-secondary-bg);
        border-radius: 12px;
        border: 1px solid var(--color-border);
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--color-border);
    }

    .section-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--color-text);
        margin: 0;
    }

    .section-body {
        /* Content goes here */
    }

    @media (max-width: 768px) {
        .page-title {
            font-size: 1.5rem;
        }

        .icon-wrapper {
            width: 48px;
            height: 48px;
        }

        .settings-section {
            padding: 1.5rem;
        }
    }
</style>
