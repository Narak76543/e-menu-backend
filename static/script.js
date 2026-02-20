const API_URL = "http://127.0.0.1:8000/users/";
const BASE_URL = "http://127.0.0.1:8000/"; // Used to prefix image paths

const userForm = document.getElementById('userForm');
const submitBtn = document.getElementById('submitBtn');
const cancelBtn = document.getElementById('cancelBtn');
const isEditMode = document.getElementById('isEditMode');
const currentUserId = document.getElementById('currentUserId');

// 1. Fetch and Display Users
async function fetchUsers() {
    const response = await fetch(API_URL);
    const users = await response.json();
    const tableBody = document.getElementById('userTableBody');
    tableBody.innerHTML = '';

    const BASE_URL = "http://127.0.0.1:8000/"; // Make sure this matches your backend URL

users.forEach(user => {
    const imgSrc = user.image_url ? `${BASE_URL}${user.image_url}` : 'https://via.placeholder.com/50';
    
    const row = `
        <tr>
            <td><img src="${imgSrc}" class="user-thumb" onerror="this.src='https://via.placeholder.com/50'"></td>
            <td>${user.name}</td>
            <td>${user.email}</td>
            <td>${user.job}</td>
            <td>
                <button class="edit-btn" onclick='prepareEdit(${JSON.stringify(user)})'>Edit</button>
                <button class="delete-btn" onclick="deleteUser(${user.id})">Delete</button>
            </td>
        </tr>
    `;
    tableBody.innerHTML += row;
});
}

// 2. Prepare Form for Edit
function prepareEdit(user) {
    document.getElementById('name').value = user.name;
    document.getElementById('email').value = user.email;
    document.getElementById('phone').value = user.phone_number || "";
    document.getElementById('job').value = user.job;
    
    currentUserId.value = user.id;
    isEditMode.value = "true";
    document.getElementById('formTitle').innerText = "Edit User: " + user.name;
    submitBtn.innerText = "Update User & Photo";
    submitBtn.style.background = "#3498db";
    cancelBtn.style.display = "inline-block";
}

// 3. Reset Form
cancelBtn.onclick = () => {
    userForm.reset();
    isEditMode.value = "false";
    document.getElementById('formTitle').innerText = "Add New User";
    submitBtn.innerText = "Create User";
    submitBtn.style.background = "#008bfe";
    cancelBtn.style.display = "none";
};

// 4. Submit Form (Create or Update)
userForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Create FormData object
    const formData = new FormData();
    formData.append('name', document.getElementById('name').value);
    formData.append('email', document.getElementById('email').value);
    formData.append('phone_number', document.getElementById('phone').value);
    formData.append('job', document.getElementById('job').value);
    
    const fileInput = document.getElementById('userImage');
    if (fileInput.files[0]) {
        formData.append('image', fileInput.files[0]);
    }

    let url = API_URL + "create/";
    let method = 'POST';

    if (isEditMode.value === "true") {
        url = `${API_URL}${currentUserId.value}`;
        method = 'PUT'; // Note: Your backend update logic must be updated to accept Form data too
    }

    // IMPORTANT: Do not set Content-Type header when sending FormData
    const response = await fetch(url, {
        method: method,
        body: formData 
    });

    if (response.ok) {
        cancelBtn.click();
        fetchUsers();
    } else {
        alert("Failed to save user data.");
    }
});

// 5. Delete User
async function deleteUser(userId) {
    if (confirm("Delete this user?")) {
        await fetch(`${API_URL}${userId}`, { method: 'DELETE' });
        fetchUsers();
    }
}

fetchUsers();