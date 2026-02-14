"""Approval panel for human-in-the-loop dangerous operations."""

from textual.app import ComposeResult
from textual.widgets import Button, Static, Label
from textual.containers import Vertical, Horizontal
from textual.widget import Widget
from textual.message import Message
from typing import Optional


class ApprovalPanel(Widget):
    """
    Big green/red button approval UI for dangerous operations.
    
    Shows pending action details and allows user to approve or reject.
    """
    
    DEFAULT_CSS = """
    ApprovalPanel {
        height: auto;
        min-height: 5;
        border: solid $primary;
        padding: 1;
        margin: 1;
    }
    
    ApprovalPanel.hidden {
        display: none;
    }
    
    ApprovalPanel #approval-title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    
    ApprovalPanel #approval-description {
        margin-bottom: 1;
    }
    
    ApprovalPanel #approval-buttons {
        height: 3;
        align: center middle;
    }
    
    ApprovalPanel #btn-approve {
        background: $success;
        color: $text;
        margin-right: 2;
        min-width: 16;
    }
    
    ApprovalPanel #btn-reject {
        background: $error;
        color: $text;
        min-width: 16;
    }
    """
    
    class Approved(Message):
        """Fired when user approves the action."""
        def __init__(self, approval_id: str) -> None:
            super().__init__()
            self.approval_id = approval_id
    
    class Rejected(Message):
        """Fired when user rejects the action."""
        def __init__(self, approval_id: str) -> None:
            super().__init__()
            self.approval_id = approval_id
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.pending_approval_id: Optional[str] = None
        self.pending_agent: str = ""
        self.pending_action: str = ""
    
    def compose(self) -> ComposeResult:
        yield Label("⚠️  APPROVAL REQUIRED", id="approval-title")
        yield Static("No pending actions", id="approval-description")
        with Horizontal(id="approval-buttons"):
            yield Button("✓ APPROVE", id="btn-approve", variant="success")
            yield Button("✗ REJECT", id="btn-reject", variant="error")
    
    def on_mount(self) -> None:
        """Start hidden until there's something to approve."""
        self.add_class("hidden")
    
    def show_approval(
        self,
        approval_id: str,
        agent: str,
        operation: str,
        description: str,
    ) -> None:
        """Display an approval request."""
        self.pending_approval_id = approval_id
        self.pending_agent = agent
        self.pending_action = operation
        
        desc_widget = self.query_one("#approval-description", Static)
        desc_widget.update(
            f"[bold cyan]{agent.upper()}[/] agent wants to:\n\n"
            f"[bold]{operation}[/]\n\n"
            f"{description}"
        )
        
        self.remove_class("hidden")
    
    def hide_approval(self) -> None:
        """Hide the approval panel."""
        self.pending_approval_id = None
        self.add_class("hidden")
        
        desc_widget = self.query_one("#approval-description", Static)
        desc_widget.update("No pending actions")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle approve/reject button clicks."""
        if not self.pending_approval_id:
            return
        
        approval_id = self.pending_approval_id
        
        if event.button.id == "btn-approve":
            # Show approval feedback
            desc_widget = self.query_one("#approval-description", Static)
            desc_widget.update("[green]✓ Action approved. Executing...[/]")
            
            # Post approval message
            self.post_message(self.Approved(approval_id))
            
            # Hide after short delay (let message be seen)
            self.set_timer(1.5, self.hide_approval)
            
        elif event.button.id == "btn-reject":
            # Show rejection feedback
            desc_widget = self.query_one("#approval-description", Static)
            desc_widget.update("[red]✗ Action rejected.[/]")
            
            # Post rejection message
            self.post_message(self.Rejected(approval_id))
            
            # Hide after short delay
            self.set_timer(1.5, self.hide_approval)
    
    @property
    def has_pending(self) -> bool:
        """Check if there's a pending approval."""
        return self.pending_approval_id is not None
