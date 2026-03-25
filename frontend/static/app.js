// Get auth data from sessionStorage
let authToken = sessionStorage.getItem('authToken');
let userData = null;

try {
    const userDataStr = sessionStorage.getItem('userData');
    if (userDataStr) {
        userData = JSON.parse(userDataStr);
    }
} catch (e) {
    console.error('Error parsing user data');
}

// Display server number
document.getElementById('serverNumber').textContent = ENV.SERVER_NUMBER;

let currentFilter = 'all';
let todos = [];

// Check authentication
if (!authToken) {
    window.location.href = 'index.html';
}

// Display username
if (userData) {
    document.getElementById('username').textContent = userData.username;
}

// Logout function
function logout() {
    sessionStorage.removeItem('authToken');
    sessionStorage.removeItem('userData');
    window.location.href = 'index.html';
}

// Fetch all todos
async function fetchTodos() {
    try {
        let url = `${ENV.API_URL}/todos`;
        if (currentFilter !== 'all') {
            url += `?status=${currentFilter}`;
        }
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            todos = data.todos || [];
            renderTodos();
        } else if (response.status === 401) {
            logout();
        }
    } catch (error) {
        console.error('Error fetching todos:', error);
    }
}

// Render todos
function renderTodos() {
    const todoList = document.getElementById('todoList');
    const emptyState = document.getElementById('emptyState');
    
    if (todos.length === 0) {
        todoList.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    
    todoList.innerHTML = todos.map(todo => `
        <div class="todo-item ${todo.completed ? 'completed' : ''}">
            <div class="todo-header">
                <input type="checkbox" 
                       class="todo-checkbox" 
                       ${todo.completed ? 'checked' : ''} 
                       onchange="toggleTodo('${todo.id}', ${!todo.completed})">
                <div class="todo-media-container">
                    ${todo.imageUrl ? 
                      `<img src="${todo.imageUrl}" alt="Todo Image" class="todo-image" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` :
                      `<button class="todo-media-placeholder" onclick="uploadMediaToTodo('${todo.id}')">
                         <span class="media-icon">📷</span>
                       </button>`
                    }
                </div>
                <div class="todo-content">
                    <div class="todo-title">${escapeHtml(todo.title)}</div>
                    <div class="todo-actions">
                        <button class="btn-delete" onclick="deleteTodo('${todo.id}')">Delete</button>
                    </div>
                </div>
            </div>
            ${todo.description ? `<div class="todo-description">${escapeHtml(todo.description)}</div>` : ''}
            <div class="todo-date">Created: ${formatDate(todo.createdAt)}</div>
        </div>
    `).join('');
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Handle file selection and display filename
document.getElementById('todoImage').addEventListener('change', function(e) {
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    if (this.files && this.files[0]) {
        const file = this.files[0];
        fileNameDisplay.textContent = file.name;
        
        // Check file size (max 5MB)
        const maxSize = 5 * 1024 * 1024; // 5MB in bytes
        if (file.size > maxSize) {
            alert('File size exceeds 5MB limit. Please select a smaller image.');
            this.value = '';
            fileNameDisplay.textContent = '';
        }
    } else {
        fileNameDisplay.textContent = '';
    }
});

// Add todo
document.getElementById('addTodoForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const title = document.getElementById('todoTitle').value;
    const description = document.getElementById('todoDescription').value;
    const imageInput = document.getElementById('todoImage');
    
    // Create FormData to send multipart data
    const formData = new FormData();
    formData.append('title', title);
    if (description) {
        formData.append('description', description);
    }
    
    // Add image if selected
    if (imageInput.files && imageInput.files[0]) {
        const file = imageInput.files[0];
        const maxSize = 5 * 1024 * 1024; // 5MB in bytes
        
        if (file.size > maxSize) {
            alert('File size exceeds 5MB limit. Please select a smaller image.');
            return;
        }
        
        formData.append('image', file);
    }
    
    try {
        const response = await fetch(`${ENV.API_URL}/todos`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
                // Don't set Content-Type manually - let browser set it with boundary
            },
            body: formData
        });
        
        if (response.ok) {
            document.getElementById('todoTitle').value = '';
            document.getElementById('todoDescription').value = '';
            document.getElementById('todoImage').value = '';
            document.getElementById('fileNameDisplay').textContent = '';
            await fetchTodos();
        } else if (response.status === 401) {
            logout();
        } else {
            const errorData = await response.json();
            console.error('Error adding todo:', errorData);
            alert(errorData.error?.message || 'Failed to add todo');
        }
    } catch (error) {
        console.error('Error adding todo:', error);
        alert('Network error. Please try again.');
    }
});

// Toggle todo completion
async function toggleTodo(id, completed) {
    try {
        const response = await fetch(`${ENV.API_URL}/todos/${id}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ completed })
        });
        
        if (response.ok) {
            await fetchTodos();
        } else if (response.status === 401) {
            logout();
        }
    } catch (error) {
        console.error('Error updating todo:', error);
    }
}

// Upload media to existing todo
async function uploadMediaToTodo(id) {
    // Create a temporary input element for file selection
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    
    fileInput.onchange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        
        // Check file size (max 5MB)
        const maxSize = 5 * 1024 * 1024; // 5MB in bytes
        if (file.size > maxSize) {
            alert('File size exceeds 5MB limit. Please select a smaller image.');
            return;
        }
        
        // Create FormData to send multipart data
        const formData = new FormData();
        formData.append('image', file);
        
        try {
            const response = await fetch(`${ENV.API_URL}/todos/${id}/image`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`
                    // Don't set Content-Type manually - let browser set it with boundary
                },
                body: formData
            });
            
            if (response.ok) {
                await fetchTodos(); // Refresh the todo list
            } else if (response.status === 401) {
                logout();
            } else {
                const errorData = await response.json();
                console.error('Error uploading media:', errorData);
                alert(errorData.error?.message || 'Failed to upload media');
            }
        } catch (error) {
            console.error('Error uploading media:', error);
            alert('Network error. Please try again.');
        }
    };
    
    // Trigger the file selection dialog
    fileInput.click();
}

// Delete todo
async function deleteTodo(id) {
    if (!confirm('Are you sure you want to delete this todo?')) {
        return;
    }
    
    try {
        const response = await fetch(`${ENV.API_URL}/todos/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok || response.status === 204) {
            await fetchTodos();
        } else if (response.status === 401) {
            logout();
        }
    } catch (error) {
        console.error('Error deleting todo:', error);
    }
}

// Filter todos
function filterTodos(filter) {
    currentFilter = filter;
    
    // Update active button
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    fetchTodos();
}

// Initial load
fetchTodos();