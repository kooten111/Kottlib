<script>
  /**
   * ConfigInput - Dynamic input component for scanner configuration
   *
   * Renders the appropriate input control based on the config option type.
   * Supports: STRING, SECRET, INTEGER, FLOAT, BOOLEAN, SELECT, MULTI_SELECT
   */
  export let option; // ConfigOption object from the schema
  export let value = null; // Current value
  export let onChange = (newValue) => {}; // Callback when value changes

  // Initialize value with default if not set
  $: if (value === null || value === undefined) {
    value = option.default !== undefined ? option.default : getDefaultValue(option.type);
  }

  // Show/hide password toggle for SECRET type
  let showPassword = false;

  function getDefaultValue(type) {
    switch (type) {
      case 'boolean':
        return false;
      case 'integer':
        return 0;
      case 'float':
        return 0.0;
      case 'multi_select':
        return [];
      default:
        return '';
    }
  }

  function handleChange(newValue) {
    value = newValue;
    onChange(newValue);
  }

  function toggleMultiSelect(optionValue) {
    const currentValues = Array.isArray(value) ? value : [];
    if (currentValues.includes(optionValue)) {
      handleChange(currentValues.filter(v => v !== optionValue));
    } else {
      handleChange([...currentValues, optionValue]);
    }
  }
</script>

<div class="config-input">
  <div class="label-row">
    <label for={option.key}>
      {option.label}
      {#if option.required}
        <span class="required">*</span>
      {/if}
    </label>
    {#if option.advanced}
      <span class="badge">Advanced</span>
    {/if}
  </div>

  {#if option.description}
    <p class="description">{option.description}</p>
  {/if}

  <div class="input-container">
    {#if option.type === 'string'}
      <input
        type="text"
        id={option.key}
        bind:value
        on:change={() => handleChange(value)}
        placeholder={option.placeholder || ''}
        required={option.required}
        class="input"
      />

    {:else if option.type === 'secret'}
      <div class="secret-input">
        <input
          type={showPassword ? 'text' : 'password'}
          id={option.key}
          bind:value
          on:change={() => handleChange(value)}
          placeholder={option.placeholder || ''}
          required={option.required}
          class="input"
        />
        <button
          type="button"
          class="toggle-password"
          on:click={() => showPassword = !showPassword}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? '👁️' : '👁️‍🗨️'}
        </button>
      </div>

    {:else if option.type === 'integer'}
      <input
        type="number"
        id={option.key}
        bind:value
        on:change={() => handleChange(value)}
        min={option.min_value}
        max={option.max_value}
        step="1"
        required={option.required}
        class="input"
      />

    {:else if option.type === 'float'}
      {#if option.min_value !== undefined && option.max_value !== undefined}
        <!-- Render as slider with value display -->
        <div class="slider-container">
          <input
            type="range"
            id={option.key}
            bind:value
            on:input={() => handleChange(value)}
            min={option.min_value}
            max={option.max_value}
            step={option.step || 0.1}
            required={option.required}
            class="slider"
          />
          <span class="slider-value">{value}</span>
        </div>
      {:else}
        <!-- Render as number input -->
        <input
          type="number"
          id={option.key}
          bind:value
          on:change={() => handleChange(value)}
          min={option.min_value}
          max={option.max_value}
          step={option.step || 0.1}
          required={option.required}
          class="input"
        />
      {/if}

    {:else if option.type === 'boolean'}
      <label class="toggle-switch">
        <input
          type="checkbox"
          id={option.key}
          bind:checked={value}
          on:change={() => handleChange(value)}
        />
        <span class="toggle-slider"></span>
      </label>

    {:else if option.type === 'select'}
      <select
        id={option.key}
        bind:value
        on:change={() => handleChange(value)}
        required={option.required}
        class="select"
      >
        {#if !option.required}
          <option value="">-- Select --</option>
        {/if}
        {#each option.options || [] as opt}
          <option value={opt}>{opt}</option>
        {/each}
      </select>

    {:else if option.type === 'multi_select'}
      <div class="checkbox-group">
        {#each option.options || [] as opt}
          <label class="checkbox-label">
            <input
              type="checkbox"
              checked={Array.isArray(value) && value.includes(opt)}
              on:change={() => toggleMultiSelect(opt)}
            />
            <span>{opt}</span>
          </label>
        {/each}
      </div>

    {:else}
      <!-- Fallback for unknown types -->
      <input
        type="text"
        id={option.key}
        bind:value
        on:change={() => handleChange(value)}
        class="input"
      />
    {/if}
  </div>
</div>

<style>
  .config-input {
    margin-bottom: 1.5rem;
  }

  .label-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
  }

  label {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text-primary, #1f2937);
  }

  .required {
    color: var(--error, #ef4444);
  }

  .badge {
    font-size: 0.75rem;
    padding: 0.125rem 0.5rem;
    background: var(--badge-bg, #e5e7eb);
    color: var(--badge-text, #6b7280);
    border-radius: 0.25rem;
    font-weight: 500;
  }

  .description {
    font-size: 0.875rem;
    color: var(--text-secondary, #6b7280);
    margin: 0 0 0.5rem 0;
  }

  .input-container {
    width: 100%;
  }

  .input,
  .select {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--border, #d1d5db);
    border-radius: 0.375rem;
    font-size: 0.95rem;
    background: var(--input-bg, white);
    color: var(--text-primary, #1f2937);
    transition: border-color 0.2s;
  }

  .input:focus,
  .select:focus {
    outline: none;
    border-color: var(--primary, #3b82f6);
    box-shadow: 0 0 0 3px var(--primary-light, rgba(59, 130, 246, 0.1));
  }

  .secret-input {
    position: relative;
    display: flex;
    align-items: center;
  }

  .secret-input .input {
    padding-right: 3rem;
  }

  .toggle-password {
    position: absolute;
    right: 0.5rem;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem;
    font-size: 1.25rem;
    opacity: 0.6;
    transition: opacity 0.2s;
  }

  .toggle-password:hover {
    opacity: 1;
  }

  .slider-container {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .slider {
    flex: 1;
    height: 0.5rem;
    border-radius: 0.25rem;
    background: var(--slider-bg, #e5e7eb);
    outline: none;
    -webkit-appearance: none;
  }

  .slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 1.25rem;
    height: 1.25rem;
    border-radius: 50%;
    background: var(--primary, #3b82f6);
    cursor: pointer;
    transition: background 0.2s;
  }

  .slider::-webkit-slider-thumb:hover {
    background: var(--primary-dark, #2563eb);
  }

  .slider::-moz-range-thumb {
    width: 1.25rem;
    height: 1.25rem;
    border-radius: 50%;
    background: var(--primary, #3b82f6);
    cursor: pointer;
    border: none;
    transition: background 0.2s;
  }

  .slider::-moz-range-thumb:hover {
    background: var(--primary-dark, #2563eb);
  }

  .slider-value {
    min-width: 3rem;
    text-align: right;
    font-weight: 600;
    color: var(--text-primary, #1f2937);
  }

  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 3rem;
    height: 1.5rem;
    cursor: pointer;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--toggle-off, #cbd5e1);
    border-radius: 1.5rem;
    transition: background-color 0.3s;
  }

  .toggle-slider::before {
    content: '';
    position: absolute;
    height: 1.125rem;
    width: 1.125rem;
    left: 0.1875rem;
    bottom: 0.1875rem;
    background-color: white;
    border-radius: 50%;
    transition: transform 0.3s;
  }

  input:checked + .toggle-slider {
    background-color: var(--primary, #3b82f6);
  }

  input:checked + .toggle-slider::before {
    transform: translateX(1.5rem);
  }

  .checkbox-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-weight: normal;
  }

  .checkbox-label input[type="checkbox"] {
    width: 1.125rem;
    height: 1.125rem;
    cursor: pointer;
  }

  .checkbox-label span {
    color: var(--text-primary, #1f2937);
  }
</style>
