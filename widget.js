// Replace with your actual GitHub Pages URL
const JSON_URL = 'https://github.com/coi-student-assistant/unt-electives-project/blob/main/electives.json';

// Gateway courses students can check off
const GATEWAY_COURSES = ["CSCE 1030", "CSCE 1040", "CSCE 2100", "CSCE 2110", "MATH 1710"];
let coursesData = [];
let completedCourses = new Set();
let showOnlyLowPrereq = false;

async function initElectivesApp() {
    const container = document.getElementById('unt-electives-app');
    
    // Inject Layout
    container.innerHTML = `
        <div class="disclaimer">
            <strong>Notice:</strong> This tool is for exploratory planning only. Official prerequisites and degree requirements are governed by the UNT Catalog and your official Degree Audit in MyUNT. Always verify your eligibility with your academic advisor.
        </div>
        <div class="controls">
            <button id="toggle-prereq-btn">Show ≤ 1 Prereq Only</button>
        </div>
        <details style="margin-bottom: 20px; cursor: pointer;">
            <summary><strong>Check courses you have already completed:</strong></summary>
            <div id="checklist-container" style="padding: 10px 0;"></div>
        </details>
        <div id="course-grid">Loading courses...</div>
    `;

    // Render Checklist
    const checkContainer = document.getElementById('checklist-container');
    GATEWAY_COURSES.forEach(course => {
        checkContainer.innerHTML += `
            <label style="margin-right: 15px; cursor: pointer;">
                <input type="checkbox" value="${course}" class="course-checkbox"> ${course}
            </label>
        `;
    });

    // Event Listeners
    document.querySelectorAll('.course-checkbox').forEach(box => {
        box.addEventListener('change', (e) => {
            if(e.target.checked) completedCourses.add(e.target.value);
            else completedCourses.delete(e.target.value);
            renderCourses();
        });
    });

    document.getElementById('toggle-prereq-btn').addEventListener('click', (e) => {
        showOnlyLowPrereq = !showOnlyLowPrereq;
        e.target.textContent = showOnlyLowPrereq ? "Show All Courses" : "Show ≤ 1 Prereq Only";
        renderCourses();
    });

    // Fetch Data
    try {
        const response = await fetch(JSON_URL);
        coursesData = await response.json();
        renderCourses();
    } catch (error) {
        document.getElementById('course-grid').innerHTML = "<p>Error loading catalog data.</p>";
    }
}

function renderCourses() {
    const grid = document.getElementById('course-grid');
    grid.innerHTML = "";

    coursesData.forEach(course => {
        // Filter by count
        if (showOnlyLowPrereq && course.prereq_count > 1) return;

        // Check if student has prerequisites
        const missingPrereqs = course.prereqs_parsed.filter(p => !completedCourses.has(p));
        const isEligible = missingPrereqs.length === 0;

        const warningHtml = course.complex_prereq ? `<span class="warning-badge">⚠️ Complex Prereqs: Read Catalog</span>` : '';
        const eligibleHtml = isEligible ? `<span style="color: green; font-weight: bold;">✓ Eligible</span>` : `<span style="color: #666;">Missing: ${missingPrereqs.join(', ')}</span>`;

        grid.innerHTML += `
            <div class="course-card">
                <h3 style="margin: 0 0 8px 0;">
                    <a href="${course.catalog_url}" target="_blank" style="color: #00853E; text-decoration: none;">
                        ${course.code}: ${course.title}
                    </a>
                    ${warningHtml}
                </h3>
                <p style="margin: 0 0 4px 0; font-size: 0.9em;"><strong>Terms:</strong> ${course.offered_terms.join(', ')}</p>
                <p style="margin: 0; font-size: 0.9em;"><strong>Status:</strong> ${eligibleHtml}</p>
            </div>
        `;
    });
}

// Boot the app
initElectivesApp();
