async function apiRequest(endpoint, method = "GET", body = null, withAuth = false) {
    const options = {
        method,
        headers: {
            "Content-Type": "application/json"
        }
    };

    if (withAuth) {
        const token = getToken();

        if (token) {
            options.headers.Authorization = `Bearer ${token}`;
        }
    }

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, options);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || data.message || "Request failed");
    }

    return data;
}

const API = {
    login(identifier, password, deviceId) {
        return apiRequest("/api/auth/login", "POST", {
            identifier,
            password,
            deviceId
        });
    },

    googleLogin(idToken, deviceId) {
        return apiRequest("/api/auth/google-login", "POST", {
            idToken,
            deviceId
        });
    },

    completePhone(phoneNumber) {
        return apiRequest("/api/users/complete-phone", "POST", {
            phone_number: phoneNumber
        }, true);
    },

    forgotPassword(email) {
        return apiRequest("/api/auth/forgot-password", "POST", {
            email
        });
    },

    resetPassword(email, otp, newPassword) {
        return apiRequest("/api/auth/reset-password", "POST", {
            email,
            otp,
            new_password: newPassword
        });
    },

    register(data) {
       return apiRequest("/api/auth/register", "POST", data);
    },

    verifyOtp(email, otp) {
       return apiRequest("/api/auth/verify-otp", "POST", {
           email,
           otp
        });
    },

resendOtp(email) {
    return apiRequest("/api/auth/resend-otp", "POST", {
        email
    });
},
getProfile() {
    return apiRequest("/api/users/profile", "GET", null, true);
},

getNotifications() {
    return apiRequest("/api/notifications", "GET", null, true);
},

readNotification(id) {
    return apiRequest(`/api/notifications/${id}/read`, "POST", null, true);
},

readAllNotifications() {
    return apiRequest("/api/notifications/read-all", "POST", null, true);
},

getPurchases() {
    return apiRequest("/api/my-purchases", "GET", null, true);
},
getStoreCourses() {
    return apiRequest("/api/store/courses", "GET", null, true);
},

getPaymentMethods() {
    return apiRequest("/api/payment-settings", "GET", null, false);
},

submitPurchase(courseId, transferNumber) {
    return apiRequest("/api/purchases", "POST", {
        course_id: courseId,
        transfer_number: transferNumber
    }, true);
},

freeEnroll(courseId) {
    return apiRequest("/api/purchases", "POST", {
        course_id: courseId,
        transfer_number: "FREE"
    }, true);
},

getMyCourses() {
    return apiRequest("/api/my-courses", "GET", null, true);
},

getCourseContent(courseId) {
    return apiRequest(`/api/courses/${courseId}/content`, "GET", null, true);
},

watchLesson(lessonId) {
    return apiRequest(`/api/lessons/${lessonId}/watch`, "GET", null, true);
},

changePassword(currentPassword, newPassword) {
    return apiRequest("/api/users/change-password", "POST", {
        current_password: currentPassword,
        new_password: newPassword
    }, true);
},

getCertificates() {
    return apiRequest("/api/my-certificates", "GET", null, true);
},

updateLessonProgress(lessonId, completed) {
    return apiRequest("/api/progress/lesson", "POST", {
        lesson_id: Number(lessonId),
        is_completed: completed
    }, true);
},

getCertificates() {
    return apiRequest("/api/my-certificates", "GET", null, true);
},
};