// ============================================================
// Genuire - Theme Controller
// ============================================================

(function() {
    // 1. Immediately apply saved theme on load to HTML element to prevent flash
    const savedTheme = localStorage.getItem('genuire-theme');
    if (savedTheme === 'light' || !savedTheme) {
        document.documentElement.classList.add('light-theme');
    }
})();

document.addEventListener('DOMContentLoaded', () => {
    // 2. Move class from html to body to match body.light-theme stylesheet selectors
    if (document.documentElement.classList.contains('light-theme')) {
        document.body.classList.add('light-theme');
        document.documentElement.classList.remove('light-theme');
    }

    // 3. Set up event listener for theme toggle button
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            document.body.classList.toggle('light-theme');
            const currentTheme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
            localStorage.setItem('genuire-theme', currentTheme);
        });
    }
});
