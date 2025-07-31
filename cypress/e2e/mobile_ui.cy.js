// Cypress E2E tests for mobile UI and booking flow

describe('Mobile UI and Booking Flow', () => {
  const iphoneWidth = 375;
  const iphoneHeight = 812;

  beforeEach(() => {
    cy.viewport(iphoneWidth, iphoneHeight);
  });

  it('Sidebar collapses on mobile view', () => {
    cy.visit('/dashboard/');
    // Sidebar should be collapsed or hidden by default on mobile
    cy.get('.sidebar, nav.sidebar').should('not.be.visible');
    // Open sidebar menu button (hamburger)
    cy.get('.sidebar-toggle, .hamburger, .menu-toggle').first().click({ force: true });
    cy.get('.sidebar, nav.sidebar').should('be.visible');
    // Collapse again
    cy.get('.sidebar-toggle, .hamburger, .menu-toggle').first().click({ force: true });
    cy.get('.sidebar, nav.sidebar').should('not.be.visible');
  });

  it('Doctor dashboard loads correctly on iPhone screen width', () => {
    // Simulate login as doctor (assume test doctor exists)
    cy.visit('/login/');
    cy.get('input[name="username"]').type('doctor_test');
    cy.get('input[name="password"]').type('testpass123');
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/dashboard');
    // Check for doctor-specific dashboard elements
    cy.contains('Doctor Dashboard').should('be.visible');
    cy.get('.appointments-list, .doctor-appointments').should('be.visible');
    // Responsive layout check
    cy.get('body').should('have.css', 'width', `${iphoneWidth}px`);
  });

  it('Booking flow is functional on mobile', () => {
    // Simulate login as patient (assume test patient exists)
    cy.visit('/login/');
    cy.get('input[name="username"]').type('patient_test');
    cy.get('input[name="password"]').type('testpass123');
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/dashboard');
    // Go to booking page
    cy.get('a[href*="/schedule"], a:contains("Book Appointment")').first().click({ force: true });
    cy.url().should('include', '/schedule');
    // Fill out booking form
    cy.get('select[name="doctor"]').select(1); // Select first doctor
    cy.get('input[name="appointment_date"]').type('2025-12-31T10:00');
    cy.get('textarea[name="notes"]').type('Mobile booking test');
    cy.get('button[type="submit"]:contains("Book")').click();
    // Should redirect to dashboard or confirmation
    cy.url().should('match', /dashboard|confirmation/);
    cy.contains('Appointment').should('be.visible');
  });
}); 