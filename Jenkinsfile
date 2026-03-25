pipeline {
    agent any

    environment {
        EC2_USER     = 'ubuntu'
        // Llamamos a la nueva función para obtener la IP
        EC2_IP       = branchIP()
        REMOTE_DIR   = "/home/ubuntu/projects/odoo_${env.BRANCH_NAME}"
        
        COMPOSE_PROJECT_NAME = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        ODOO_PORT            = branchPort()
        POSTGRES_DB          = "odoo_${env.BRANCH_NAME.replaceAll('[^a-zA-Z0-9]', '_')}"
        POSTGRES_USER        = 'odoo'
        POSTGRES_PASSWORD    = credentials('odoo-db-password')
    }

    stages {
        stage('Deploy to EC2') {
            steps {
                sshagent(['ec2-odoo-key']) {
                    sh '''
                        echo "Desplegando rama ${BRANCH_NAME} en la IP ${EC2_IP}..."
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_IP} "mkdir -p ${REMOTE_DIR}"
                        scp -r ./* ${EC2_USER}@${EC2_IP}:${REMOTE_DIR}
                        
                        ssh ${EC2_USER}@${EC2_IP} << EOF
                            cd ${REMOTE_DIR}
                            export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
                            export ODOO_PORT=${ODOO_PORT}
                            export POSTGRES_DB=${POSTGRES_DB}
                            export POSTGRES_USER=${POSTGRES_USER}
                            export POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
                            
                            docker compose up -d --build --remove-orphans
                            sleep 15
                            docker compose exec -T odoo odoo -d ${POSTGRES_DB} -u all --stop-after-init
                            docker compose restart odoo
EOF
                    '''
                }
            }
        }
    }
    // ... post y branchPort se mantienen igual
}

// NUEVA FUNCIÓN: Asigna IP según la rama
def branchIP() {
    switch (env.BRANCH_NAME) {
        case 'main':    return '3.144.231.64'   // IP de Producción
        case 'staging': return '18.219.33.101'  // IP de Staging
        default:        return '18.219.33.101'  // Por defecto a Staging
    }
}

def branchPort() {
    switch (env.BRANCH_NAME) {
        case 'main':    return '8071'
        case 'staging': return '8070'
        default:        return '8069'
    }
}