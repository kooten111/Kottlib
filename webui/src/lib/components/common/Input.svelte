<script>
	export let type = 'text';
	export let value = '';
	export let placeholder = '';
	export let disabled = false;
	export let required = false;
	export let id = undefined;
	export let name = undefined;
	export let autocomplete = undefined;
</script>

<input
	{type}
	{id}
	{name}
	{placeholder}
	{disabled}
	{required}
	{autocomplete}
	bind:value
	class="input w-full"
	on:input
	on:change
	on:focus
	on:blur
/>
